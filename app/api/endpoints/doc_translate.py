import io
import re
import asyncio
from openai import AsyncOpenAI
from app.core.providers import get_provider
from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect
    )
from docx import Document


router = APIRouter()


# 定义术语标记函数
def mark_terms_in_text(text, terms):
    if not text or not terms:
        return {
            "marked_text": text,
            "found_terms": [],
        }

    # 标准化术语表格式，并按照长度排序
    glossary = [item["term"].lower() for item in terms]
    glossary.sort(key=len, reverse=True)

    found_terms = []
    marked_text = text

    # 逐个匹配术语
    for term in glossary:
        if not term.strip():
            continue

        # 使用正则表达式进行全词匹配
        pattern_string = r'\b' + re.escape(term) + r'\b'
        pattern = re.compile(pattern_string, re.IGNORECASE)
        matches = list(pattern.finditer(marked_text))

        if matches:
            found_terms.append(term)

            # 从前往后替换，避免位置偏移
            for match in reversed(matches):
                start, end = match.span()
                original_term = marked_text[start:end]
                marked_term = f"[[[TERM_START|{original_term}]]]"
                marked_text = marked_text[:start] + marked_term + marked_text[end:]

    return {
        "marked_text": marked_text,
        "found_terms": found_terms
    }


@router.websocket("/ws/translate")
async def websocket_translate(websocket: WebSocket):
    await websocket.accept()
    try:
        # 前端分别发送参数和文件内容
        params = await websocket.receive_json()
        data = await websocket.receive_bytes()
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        total = len(paragraphs)

        # 读取术语表
        terms = params.get("terms", [])

        # 读取provider配置
        primary_provider = params.get("primary_provider", "deepseek")
        optimized_provider = params.get("optimized_provider", "deepseek")
        primary_cfg = get_provider(primary_provider)
        optimized_cfg = get_provider(optimized_provider)
        temperature = params.get("temperature", 0.5)
        prompt_translate = params.get("prompt_translate")
        prompt_optimized = params.get("prompt_optimized")
        lang = params.get("lang")
        target_lang = params.get("target_lang", "中文")
        enhance = params.get("enhance", False)

        # 初始化翻译和优化client
        primary_client = AsyncOpenAI(
            api_key=primary_cfg["api_key"],
            base_url=primary_cfg["base_url"]
        )
        optimized_client = AsyncOpenAI(
            api_key=optimized_cfg["api_key"],
            base_url=optimized_cfg["base_url"]
        )

        # 定义单段落异步翻译函数
        async def translate_single_paragraph(idx, para):
            initial_translation_content = None
            optimized_translation_content = None
            # 组织翻译message
            system_prompt_1 = (
                f"请将以下{lang or '外文'}文本翻译为自然流畅的{target_lang}，在翻译之前确保充分理解上下文语境，注意文化差异、语气和语言风格。"
                )
            if prompt_translate:
                system_prompt_1 += f"\n{prompt_translate}"
            # 进行初翻译
            try:
                response_1 = await primary_client.chat.completions.create(
                    model=primary_cfg["model"],
                    messages=[
                        {"role": "system", "content": system_prompt_1},
                        {"role": "user", "content": para}
                    ],
                    temperature=temperature
                )
                initial_translation_content = response_1.choices[0].message.content
            except Exception as e:
                # 记录发生的错误
                print(f"在翻译段落'{para[:30]}...'发生了错误:{e}")
                initial_translation_content = f"[错误：翻译失败 - {type(e).__name__}]"

            # ---优化翻译阶段（如果适用）---
            # 仅当初始翻译成功且enhance为True时尝试优化
            if enhance and optimized_client and optimized_cfg and initial_translation_content and not initial_translation_content.startswith("[错误："):
                system_prompt_2 = (
                    f"""你是一位高水平的翻译，请优化以下初译{target_lang}文本，请在忠实原文（含细节与语义）的基础上，进一步提升表达自然度与语感。
                    你可以按照如下的步骤进行思考：第一步：分析原文意图与难点；第二步：指出初译可能的问题；第三步：给出优化译文。
                    请保证只输出优化后的译文，不要输出任何说明，除非极其必要。
                    """
                )
                if prompt_optimized:
                    system_prompt_2 += f"\n{prompt_optimized}"
                try:
                    response_2 = await optimized_client.chat.completions.create(
                        model=optimized_cfg["model"],
                        messages=[
                            {"role": "system", "content": system_prompt_2},
                            {"role": "user", "content": f"原文：{para}\n初译：{initial_translation_content}"}
                        ],
                        temperature=temperature
                    )
                    optimized_translation_content = response_2.choices[0].message.content
                except Exception as e:
                    print(f"在优化段落'{para[:30]}...'发生了错误:{e}")
                    pass  # 如果优化失败，则直接设置optimized_translation_content为None
                
            result = {"initial": initial_translation_content}

            if enhance and optimized_translation_content:
                result["optimized"] = optimized_translation_content

            if terms:
                result["marked_text"] = mark_terms_in_text(para, terms)["marked_text"]

            return idx, result
        
        tasks = [
            asyncio.create_task(translate_single_paragraph(i, para))
            for i, para in enumerate(paragraphs)
        ]

        results = [None] * len(paragraphs)  # 保证输出顺序
        done = 0

        for coro in asyncio.as_completed(tasks):
            idx, translation = await coro
            results[idx] = translation
            done += 1  # 更新已完成段落数

            await websocket.send_json({
                "type": "progress",
                "current": done,
                "total": total,
                "result": translation
            })

        # 全部结束后发送“完成”信息
        await websocket.send_json({
            "type": "done",
            "total": total,
            "results": results
        })
    except WebSocketDisconnect:
        print("WebSocket disconnected")
