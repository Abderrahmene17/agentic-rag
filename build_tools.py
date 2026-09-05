"""
tools.py — the actions the agent is allowed to take. Each function is one
tool: a clear name, a docstring the LLM reads to decide when to call it,
explicit typed arguments, one job.

Reads (get_document, search_documents, list_document_types) are safe —
give the agent free rein.

Writes are split in two on purpose:
  - propose_type_update: read-only, just drafts the change and returns it.
  - apply_type_update: the actual write.

Your orchestrator (the loop that runs the agent) must only call
apply_type_update after the USER has explicitly confirmed a proposal —
never let the agent chain straight from propose to apply on its own.
That gating logic lives outside this file, in the loop that decides which
tool results to feed back to the model.
"""

from db import get_connection
from embder import get_embedding


def get_document(doc_id: int) -> dict:
    """Fetch one document by its id, full content included.
    Use when you already know exactly which document you need."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, type, text FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            if row is None:
                return {"error": f"No document with id {doc_id}"}
            return {"id": row[0], "type": row[1], "text": row[2]}


def search_documents(query: str, doc_type: str | None = None, top_k: int = 5) -> list[dict]:
    """Semantic search over document content. Returns the matched excerpt,
    the document's type, and its id for each hit — not the full document.
    Use when the user asks to find or locate documents by topic or content.
    Pass doc_type to narrow the search if the user names a document type."""
    query_embedding = get_embedding(query)

    sql = "SELECT id, type, text, 1 - (embedding <=> %s::vector) AS similarity FROM documents"
    params = [query_embedding]

    if doc_type:
        sql += " WHERE type = %s"
        params.append(doc_type)

    sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
    params += [query_embedding, top_k]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "type": r[1],
            "matched_excerpt": r[2][:500],  # excerpt only, not the whole doc
            "similarity": round(r[3], 4),
        }
        for r in rows
    ]


def list_document_types() -> list[str]:
    """Return every distinct document type currently in the database.
    Use before filtering a search by type, or before proposing a type
    correction, so you never invent a type that doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT type FROM documents ORDER BY type")
            return [r[0] for r in cur.fetchall()]


def propose_type_update(doc_id: int, new_type: str) -> dict:
    """Draft a reclassification WITHOUT writing to the database. Returns the
    current type vs the proposed type so it can be shown to the user for
    confirmation. Always call this before apply_type_update."""
    doc = get_document(doc_id)
    if "error" in doc:
        return doc
    return {
        "doc_id": doc_id,
        "current_type": doc["type"],
        "proposed_type": new_type,
        "status": "pending_confirmation",
    }


def apply_type_update(doc_id: int, new_type: str) -> dict:
    """Write a document's type to the database. DESTRUCTIVE. Only call this
    after the user has explicitly confirmed a proposal from
    propose_type_update earlier in this conversation. Never call this on
    your own initiative."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET type = %s WHERE id = %s RETURNING id",
                (new_type, doc_id),
            )
            updated = cur.fetchone()
            conn.commit()
    if not updated:
        return {"error": f"No document with id {doc_id}"}
    return {"doc_id": doc_id, "new_type": new_type, "status": "updated"}