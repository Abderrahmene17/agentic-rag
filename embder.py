"""
embedder.py — turns text into a vector using sentence-transformers,
running locally on your machine. Free, no API key, no availability issues
(unlike Groq's embeddings, which turned out unreliable — see the model
error you hit).

Install:
    pip install sentence-transformers

First run downloads the model (~90MB) once, then it's cached locally.

IMPORTANT: every row's `text` column must be embedded with this SAME
function — the query embedding and the stored embeddings must come from
the same model/dimension or similarity search silently returns garbage.
"""

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # must match the `vector(N)` size in your ALTER TABLE

_model = SentenceTransformer(EMBEDDING_MODEL)


def get_embedding(text: str) -> list[float]:
    return _model.encode(text).tolist()