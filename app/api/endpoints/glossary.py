import sqlite3
from fastapi import APIRouter, HTTPException, Query
from app.models.glossary import (
    GlossaryTerm, GlossaryTermIn, DeleteGlossaryTermIn, GlossaryResponse
)
from app.db.database import get_db
from datetime import datetime

router = APIRouter()


@router.get("/all", response_model=GlossaryResponse)
def get_all_glossary_terms(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200)
):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM glossary")
        total = c.fetchone()[0]

        offset = (page - 1) * per_page
        c.execute("""
            SELECT term, translation, updated_at
            FROM glossary
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        terms = [
            GlossaryTerm(
                term=row[0],
                translation=row[1],
                updated_at=row[2]
            ) for row in c.fetchall()
        ]

        return GlossaryResponse(
            terms=terms,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=(total + per_page - 1) // per_page
        )


@router.post("/add")
def add_glossary_term(term_in: GlossaryTermIn):
    with get_db() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        try:
            c.execute("""
                INSERT INTO glossary (term, translation, updated_at)
                VALUES (?, ?, ?)
            """, (term_in.term.lower(), term_in.translation, now))
            conn.commit()
            return {"status": "success"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="术语已存在")


@router.post("/delete")
def delete_glossary_term(term_in: DeleteGlossaryTermIn):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM glossary WHERE term = ?", (term_in.term.lower(),)
            )
        conn.commit()
        deleted = c.rowcount
        if deleted:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="术语不存在")


@router.post("/update")
def update_glossary_term(term_in: GlossaryTermIn):
    with get_db() as conn:
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute(
            """UPDATE glossary SET translation = ?,
            updated_at = ?
            WHERE term = ?""",
            (term_in.translation, now, term_in.term.lower())
        )
        conn.commit()
        if c.rowcount:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=404, detail="术语不存在")
