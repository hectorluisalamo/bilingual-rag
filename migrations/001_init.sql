CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  source_uri TEXT NOT NULL,
  source_type TEXT NOT NULL, -- pdf,url,faq
  lang TEXT NOT NULL,        -- en,es,spanglish
  country TEXT,
  topic TEXT,
  version INTEGER DEFAULT 1,
  approved BOOLEAN DEFAULT TRUE,
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY,
  doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INTEGER,
  text TEXT NOT NULL,
  tokens INTEGER,
  embedding vector(1536),   -- 1536 for text-embedding-3
  section TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_documents_lang ON documents(lang);
CREATE INDEX IF NOT EXISTS idx_documents_topic ON documents(topic);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
