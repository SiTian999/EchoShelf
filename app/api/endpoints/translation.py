from fastapi import APIRouter, HTTPException, Path
from datetime import datetime
from app.models.translation import (
    TranslateRequest,
    SaveTranslationRequest,
    SaveTranslationResponse,
    TranslationHistoryItem,
    TranslationHistoryResponse
)
from app.core.providers import get_provider
from openai import OpenAI
from app.db.database import get_db

router = APIRouter()


@router.post("/api/translate")
def translate_text(request: TranslateRequest):
    # 选择 provider
    primary_cfg = get_provider(request.primary_provider)
    optimization_cfg = get_provider(
        request.optimization_provider or request.primary_provider
    )

    # 初始化客户端
    primary_client = OpenAI(
        api_key=primary_cfg["api_key"],
        base_url=primary_cfg["base_url"]
    )
    optimization_client = OpenAI(
        api_key=optimization_cfg["api_key"],
        base_url=optimization_cfg["base_url"]
    )

    # 组织 messages
    system_prompt_1 = f"请将以下{request.lang}文本翻译为自然流畅的{request.targetLang}："
    if request.customPrompt:
        system_prompt_1 += f"\n{request.customPrompt}"
    messages_1 = [
        {"role": "system", "content": system_prompt_1},
        {"role": "user", "content": request.text}
    ]

    try:
        # 第一次翻译
        response1 = primary_client.chat.completions.create(
            model=primary_cfg["model"],
            messages=messages_1,
            temperature=request.temperature,
        )
        initial = response1.choices[0].message.content.strip()

        if request.enhance:
            # 第二轮优化
            system_prompt_2 = (
                "你是一位高水平的翻译，请优化以下初译，使其更忠实原文且表达自然，请保证只输出优化后的译文，不要输出任何说明，除非极其必要。"
            )
            if request.customPrompt:
                system_prompt_2 += f"\n{request.customPrompt}"
            messages_2 = [
                {"role": "system", "content": system_prompt_2},
                {
                    "role": "user",
                    "content": f"原文：{request.text}\n初译：{initial}\n请优化翻译："
                }
            ]
            response2 = optimization_client.chat.completions.create(
                model=optimization_cfg["model"],
                messages=messages_2,
                temperature=request.temperature,
            )
            optimized = response2.choices[0].message.content.strip()
            return {
                "initial": initial,
                "optimized": optimized,
                "targetLang": request.targetLang
            }
        else:
            return {
                "translation": initial,
                "targetLang": request.targetLang
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/translation", response_model=SaveTranslationResponse)
def save_translation(request: SaveTranslationRequest):
    original_text = request.text or ''
    translated_text = request.translation or ''
    target_language = request.targetLang or ''
    timestamp = datetime.now().isoformat()

    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO translations (original_text, translated_text, target_language, timestamp) VALUES (?, ?, ?, ?)',
            (original_text, translated_text, target_language, timestamp)
        )
        conn.commit()
    return {"status": "success"}


@router.get("/api/translation/history",
            response_model=TranslationHistoryResponse)
def get_translation_history():
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            'SELECT id, original_text, translated_text, target_language, timestamp FROM translations ORDER BY timestamp DESC')
        rows = c.fetchall()
        translations = [
            TranslationHistoryItem(
                id=row[0],
                original_text=row[1],
                translated_text=row[2],
                target_language=row[3],
                timestamp=row[4]
            ) for row in rows
        ]
    return {"translations": translations}


# 删除翻译历史记录接口
@router.delete("/api/translation/{translation_id}", status_code=204)
def delete_translation(translation_id: int = Path(...,
                       description="要删除的翻译记录ID")):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM translations WHERE id = ?", (translation_id,))
        if c.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Translation not found")
        conn.commit()
    return
