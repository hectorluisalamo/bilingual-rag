from api.rag.chunk import split_sentences, chunk_by_tokens

def test_sentence_split():
    s = "Hola. ¿Cómo estás? Bien!"
    assert len(split_sentences(s)) == 3

def test_chunk_overlap():
    sents = [f"sent {i}" for i in range(50)]
    chunks = chunk_by_tokens(sents, max_tokens=10, overlap=2, count_tokens=lambda x:1)
    assert all(t <= 10 for _,t in chunks)
