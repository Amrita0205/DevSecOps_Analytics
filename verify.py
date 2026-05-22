from db.connection import get_db_cursor

with get_db_cursor() as cur:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('reports', 'insights') ORDER BY table_name")
    tables = [row[0] for row in cur.fetchall()]
    print(f'Tables found: {tables}')

    cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
    ext = cur.fetchone()
    print(f'Vector extension: {ext[0]} v{ext[1]}')

    cur.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'insights_embedding_idx'")
    idx = cur.fetchone()
    print(f'Index found: {idx[0]}')

print('All checks passed!')