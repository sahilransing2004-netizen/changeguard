import json
import math
import os
from pathlib import Path

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
KB_PATH = Path(__file__).resolve().parent.parent / "kb" / "knowledge.json"
MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.60"))

_index = None


def rag_enabled() -> bool:
    return os.getenv("CHANGEGUARD_USE_RAG", "0") == "1"


def _embed(texts: list[str]) -> list[list[float]]:
    r = httpx.post(f"{OLLAMA_URL}/api/embed",
                   json={"model": EMBED_MODEL, "input": texts}, timeout=120)
    r.raise_for_status()
    return r.json()["embeddings"]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _load():
    global _index
    if _index is None:
        docs = json.loads(KB_PATH.read_text())
        vecs = _embed([f"search_document: {d['title']}. {d['text']}" for d in docs])
        _index = list(zip(docs, vecs))
    return _index


def retrieve(query: str, k: int = 3) -> list[dict]:
    """Return up to k relevant docs (with a 'score'), or [] on any failure."""
    try:
        index = _load()
        q = _embed([f"search_query: {query}"])[0]
    except (httpx.HTTPError, KeyError, ValueError, OSError):
        return []
    scored = sorted(((_cosine(q, v), d) for d, v in index), key=lambda x: -x[0])
    return [dict(d, score=round(s, 3)) for s, d in scored[:k] if s >= MIN_SCORE]
