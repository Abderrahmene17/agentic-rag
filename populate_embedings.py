"""
populate_embeddings.py — run ONCE after migration.sql, to backfill an
embedding for every row that doesn't have one yet.

New rows inserted after this point still need to be embedded when inserted
(not covered here — that's an insert-time concern, ask me if you need it).
"""

from db import get_connection
from embder import get_embedding

BATCH_SIZE = 50

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, text FROM documents WHERE embedding IS NULL")
        rows = cur.fetchall()

    print(f"Embedding {len(rows)} rows...")

    for i, (doc_id, text) in enumerate(rows, start=1):
        embedding = get_embedding(text)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET embedding = %s WHERE id = %s",
                (embedding, doc_id),
            )
        if i % BATCH_SIZE == 0:
            conn.commit()
            print(f"  {i}/{len(rows)} done")

    conn.commit()

print("Done.")