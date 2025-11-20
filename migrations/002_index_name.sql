ALTER TABLE documents ADD COLUMN IF NOT EXISTS index_name TEXT DEFAULT 'default';
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS index_name TEXT DEFAULT 'default';

CREATE INDEX IF NOT EXISTS idx_documents_index_name ON documents(index_name);
CREATE INDEX IF NOT EXISTS idx_chunks_index_name ON chunks(index_name);
