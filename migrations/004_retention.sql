ALTER TABLE documents ADD COLUMN IF NOT EXISTS deleted BOOLEAN DEFAULT FALSE;
CREATE OR REPLACE VIEW v_latest_docs AS
SELECT DISTINCT ON (source_uri) *
FROM documents
WHERE approved = TRUE AND deleted = FALSE
ORDER BY source_uri, version DESC, fetched_at DESC;
