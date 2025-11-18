import asyncio
from api.rag.embed import embed_texts

def test_embedding():
    texts = ["arepas de maíz", "pozole rojo"]
    v1 = asyncio.run(embed_texts(texts))
    v2 = asyncio.run(embed_texts(texts))
    assert v1 == v2
