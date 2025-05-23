from pydantic import BaseModel
# from typing import Optional
from datetime import datetime


class GlossaryTerm(BaseModel):
    term: str
    translation: str
    updated_at: datetime


class GlossaryTermIn(BaseModel):
    term: str
    translation: str


class DeleteGlossaryTermIn(BaseModel):
    term: str


class GlossaryResponse(BaseModel):
    terms: list[GlossaryTerm]
    total: int
    page: int
    per_page: int
    total_pages: int
