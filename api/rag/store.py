import uuid
from sqlalchemy import text
from api.core.db import engine

def upsert_document(conn, source_uri, source_type, lang, country=None, topic=None,
                    version=1, published_at=None, index_name="default", approved=True):
    doc_id = uuid.uuid4()
    conn.execute(text("""
        INSERT INTO documents (id, source_uri, source_type, lang, country, topic,
                               version, published_at, index_name, approved)
        VALUES (:id,:uri,:stype,:lang,:country,:topic,:version,:published_at,:index_name,:approved)
    """), dict(id=str(doc_id), uri=source_uri, stype=source_type, lang=lang, country=country,
               topic=topic, version=version, published_at=published_at,
               index_name=index_name, approved=approved))
    return doc_id

def insert_chunks(conn, doc_id, chunks_with_vecs, index_name="default"):
    for idx, (text_chunk, tokens, vec, section) in enumerate(chunks_with_vecs):
        conn.execute(text("""
            INSERT INTO chunks (id, doc_id, chunk_index, text, tokens, embedding, section, index_name)
            VALUES (:id, :doc_id, :idx, :text, :tokens, :embedding, :section, :index_name)
        """), dict(id=str(uuid.uuid4()), doc_id=str(doc_id), idx=idx, text=text_chunk, tokens=tokens, embedding=vec, section=section, index_name=index_name))
