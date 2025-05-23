import json
import asyncio
import io
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from app.core.providers import get_provider
from openai import AsyncOpenAI
from docx import Document


router = APIRouter()


@router.post("/term_extract_batch")
async def extract_terms_from_docx(
    file: UploadFile = File(...),
    extraction_provider: str = Form(...)
        ):
    # 读取文件并分段
    doc_content = await file.read()
    doc = Document(io.BytesIO(doc_content))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    # 定义单个段落的提取协程
    async def extract_single_paragraph(para):
        try:
            # 选择术语提取Provider
            extraction_cfg = get_provider(extraction_provider)
            # 初始化客户端
            extraction_client = AsyncOpenAI(
                api_key=extraction_cfg["api_key"],
                base_url=extraction_cfg["base_url"]
            )

            response = await extraction_client.chat.completions.create(
                model=extraction_cfg["model"],
                messages=[
                    {"role": "system", "content": (
                        "你是一个术语提取助手。请从用户提供的文本中提取术语，并严格按照 JSON 格式返回：\n"
                        '{ "terms": ["术语1", "术语2", "术语3"] }\n'
                        "注意：请勿输出解释说明，仅输出合法 JSON 对象。"
                    )},
                    {"role": "user", "content": para}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            try:
                terms_json = json.loads(content)
            except json.JSONDecodeError:
                return JSONResponse(status_code=500, content={"error": "模型返回了非法JSON"})
            return terms_json
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    # 并发处理所有段落
    results = await asyncio.gather(*[extract_single_paragraph(p) for p in paragraphs])

    # 合并所有术语并去重（不区分大小写），以其小写形式为索引，保留原始格式
    all_terms_dict = {}
    for result in results:
        for term in result['terms']:
            lower_term = term.lower()
            if lower_term not in all_terms_dict:
                all_terms_dict[lower_term] = term  # 保留首次出现的原始形式

    # 合并全文，统计词频
    full_text = ''.join(paragraphs).lower()
    terms_with_count = []
    for lower_term, original_term in all_terms_dict.items():
        count = full_text.count(lower_term)
        terms_with_count.append({"term": original_term, "count": count})

    return {"terms": terms_with_count}
