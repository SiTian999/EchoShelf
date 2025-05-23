from pydantic import BaseModel
from typing import List


class TranslateRequest(BaseModel):
    text: str
    lang: str
    targetLang: str = "中文"
    enhance: bool = False
    customPrompt: str = ""
    primary_provider: str = "deepseek"
    optimization_provider: str = None
    temperature: float = 0.5


class TranslateResponse(BaseModel):
    translation: str
    targetLang: str


class EnhancedTranslateResponse(BaseModel):
    initial: str
    optimized: str
    targetLang: str


class SaveTranslationRequest(BaseModel):
    text: str
    translation: str
    lang: str
    targetLang: str


class SaveTranslationResponse(BaseModel):
    status: str


class TranslationHistoryItem(BaseModel):
    id: int
    original_text: str
    translated_text: str
    target_language: str
    timestamp: str


class TranslationHistoryResponse(BaseModel):
    translations: List[TranslationHistoryItem]
