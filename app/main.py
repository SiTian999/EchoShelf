from fastapi import FastAPI
from app.api.endpoints import glossary
from app.api.endpoints import term_extract
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.endpoints import translation
from app.api.endpoints import doc_translate
from dotenv import load_dotenv

load_dotenv()  # 确保 .env 被自动加载

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或者指定你的前端源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 术语管理
app.include_router(glossary.router, prefix="/api/glossary", tags=["glossary"])

# 文段翻译
app.include_router(translation.router, tags=["translate"])

# 文档翻译
app.include_router(
    doc_translate.router, prefix="/api/doc_translate", tags=["translate"]
    )

# 术语提取
app.include_router(
    term_extract.router, prefix="/api/term_extract", tags=["glossary"]
    )

# 前端页面
app.mount("/static", StaticFiles(directory="static"), name="static")
