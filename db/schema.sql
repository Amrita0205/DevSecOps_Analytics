CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS reports(
    id SERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS insights (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES reports(id),
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    insight_date DATE NOT NULL,
    raw_text TEXT NOT NULL,
    tags TEXT[], --This represents the text array
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS insights_embedding_idx
    ON insights
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);