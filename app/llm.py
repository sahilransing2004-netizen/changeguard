import json
import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SYSTEM = """You are a production change-risk reviewer for a DevOps team.
Given a diff, list concrete ways deploying it could break production, then score the risk.

Scoring rubric:
- 0-29 low: docs, comments, tests, small app-code tweaks.
- 30-59 medium: infra sizing, dependency bumps, CI changes, config tweaks.
- 60-100 high: database migrations, deleting resources, networking/security changes, anything irreversible.
Infrastructure (terraform, kubernetes), database and config changes are NEVER below 30.
Every change has some risk; name what could actually break.

Reply ONLY with JSON, reasons FIRST, then score:
{"reasons": ["<short specific risk>", "..."], "risk_score": <integer 0-100>}

Example input: redis maxmemory-policy changed from allkeys-lru to noeviction in redis.conf
Example output: {"reasons": ["noeviction makes writes fail with OOM errors when memory fills", "Cache-dependent services may start returning 5xx"], "risk_score": 62}
"""


def llm_enabled() -> bool:
    return os.getenv("CHANGEGUARD_USE_LLM", "0") == "1"


def ask_llm(title: str, diff: str, categories: list[str],
            context: list[dict] | None = None) -> dict | None:
    """Return {"risk_score": int, "reasons": [str]} or None on any failure."""
    user = (
        f"Title: {title or '(none)'}\n"
        f"Detected categories: {', '.join(categories)}\n"
        f"Diff:\n{diff[:6000]}"
    )
    if context:
        notes = "\n".join(f"[{d['id']}] {d['title']}: {d['text']}" for d in context)
        user += ("\n\nRelevant past incidents and runbooks (use only if truly relevant, "
                 "and cite the id in a reason):\n" + notes)
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=120,
        )
        r.raise_for_status()
        data = json.loads(r.json()["message"]["content"])
        score = max(0, min(100, int(data["risk_score"])))
        reasons = [str(x) for x in data["reasons"]][:5]
        return {"risk_score": score, "reasons": reasons}
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return None
