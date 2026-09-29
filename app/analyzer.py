from .models import ChangeSummary, Verdict, RiskLevel

BASE_WEIGHTS = {"terraform": 30, "database": 30, "kubernetes": 20,
                "config": 15, "ci": 10, "docker": 10, "app": 5}

import re

DESTRUCTIVE_PATTERNS = [
    r"\bDROP\s+(TABLE|COLUMN|DATABASE|INDEX)\b",
    r"\bTRUNCATE\b",
    r"\bDELETE\s+FROM\b",
    r"terraform\s+destroy",
    r"replicas:\s*0\b",
    r"\bkubectl\s+delete\b",
]


def find_destructive(diff: str) -> list[str]:
    added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    text = "\n".join(added)
    return [p for p in DESTRUCTIVE_PATTERNS if re.search(p, text, flags=re.I)]


def heuristic_verdict(summary: ChangeSummary, diff: str = "") -> Verdict:
    score = sum(BASE_WEIGHTS.get(c, 5) for c in summary.categories)
    score += min((summary.added + summary.removed) // 20, 20)
    destructive = find_destructive(diff)
    if destructive:
        score = max(score, 70)
    score = min(score, 100)
    level = RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW
    reasons = [f"Touches {c} files" for c in summary.categories]
    if destructive:
        reasons.insert(0, "Contains destructive operation (drop/delete/truncate/destroy)")
    reasons.append(f"{summary.added} lines added, {summary.removed} removed")
    return Verdict(risk_score=score, level=level, reasons=reasons, summary=summary)


def analyze(diff: str, title: str, summary: ChangeSummary) -> Verdict:
    from . import rag
    from .llm import ask_llm, llm_enabled

    baseline = heuristic_verdict(summary, diff)
    if not llm_enabled():
        return baseline
    related = []
    if rag.rag_enabled() and baseline.risk_score >= 30:
        added = "\n".join(l[1:] for l in diff.splitlines()
                          if l.startswith("+") and not l.startswith("+++"))
        related = rag.retrieve(f"{title}\n{' '.join(summary.categories)}\n{added[:1500]}")
    result = ask_llm(title, diff, summary.categories, related)
    if result is None:
        return baseline
    score = max(result["risk_score"], baseline.risk_score)
    reasons = result["reasons"] + [r for r in baseline.reasons if r not in result["reasons"]][:2]
    level = RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW
    return Verdict(risk_score=score, level=level, reasons=reasons[:6],
                   summary=summary, source="llm",
                   related_incidents=[d["id"] for d in related])
