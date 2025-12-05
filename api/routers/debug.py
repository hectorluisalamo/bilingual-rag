from fastapi import APIRouter
from sqlalchemy import text
from api.core.db import engine

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/counts")
def counts():
    with engine.connect() as conn:
        docs = conn.execute(text("""
          SELECT index_name, topic, COUNT(*) AS n_docs
          FROM documents
          WHERE approved = TRUE AND deleted = FALSE
          GROUP BY 1,2
          ORDER BY 1,2
        """)).mappings().all()
        chunks = conn.execute(text("""
          SELECT index_name, COUNT(*) AS n_chunks
          FROM chunks
          GROUP BY 1
          ORDER BY 1
        """)).mappings().all()
    return {"docs": list(docs), "chunks": list(chunks)}
