import asyncio, math
from api.rag.embed import embed_texts

def _cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)) or 1.0
    nb = math.sqrt(sum(y*y for y in b)) or 1.0
    return dot / (na * nb)

def test_embedding_shape_and_stability():
    texts = ["arepas de maíz", "pozole rojo"]
    v1 = asyncio.run(embed_texts(texts))
    v2 = asyncio.run(embed_texts(texts))
    # same batch size and dims
    assert len(v1) == len(v2) == 2
    assert all(len(v1[i]) == len(v2[i]) for i in range(2))
    # strong cosine agreement (allow tiny float jitter)
    for i in range(2):
        cos = _cosine(v1[i], v2[i])
        assert cos >= 0.999999, f"cosine too low for item {i}: {cos}"
