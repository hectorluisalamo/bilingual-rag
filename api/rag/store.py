import uuid
from sqlalchemy import create_engine, text
from api.core.config import settings

engine = create_engine(settings.db_url, pool_pre_ping=True)

def upsert_document(conn, source_uri, source_type, lang, country=None, topic=None, version=1, published_at=None):
    doc_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO documents (id, source_uri, source_type, lang, country, topic, version, published_at)
        VALUES (:id,:uri,:stype,:lang,:country,:topic,:version,:published_at)
    """), dict(id=str(doc_id), uri=source_uri, stype=source_type, lang=lang, country=country, topic=topic, version=version, published_at=published_at))
    return doc_id

def insert_chunks(conn, doc_id, chunks_with_vecs):
    for idx, (text_chunk, tokens, vec, section) in enumerate(chunks_with_vecs):
        conn.execute(text("""
            INSERT INTO chunks (id, doc_id, chunk_index, text, tokens, embedding, section)
            VALUES (:id, :doc_id, :idx, :text, :tokens, :embedding, :section)
        """), dict(id=str(uuid.uuid4()), doc_id=str(doc_id), idx=idx, text=text_chunk, tokens=tokens, embedding=vec, section=section))
