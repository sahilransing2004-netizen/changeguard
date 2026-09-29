from .models import ChangeSummary, Verdict, RiskLevel

BASE_WEIGHTS = {"terraform": 30, "database": 30, "kubernetes": 20,
                "config": 15, "ci": 10, "docker": 10, "app": 5}

def heuristic_verdict(summary: ChangeSummary) -> Verdict:
    score = sum(BASE_WEIGHTS.get(c, 5) for c in summary.categories)
    score += min((summary.added + summary.removed) // 20, 20)
    score = min(score, 100)
    level = RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW
    reasons = [f"Touches {c} files" for c in summary.categories]
    reasons.append(f"{summary.added} lines added, {summary.removed} removed")
    return Verdict(risk_score=score, level=level, reasons=reasons, summary=summary)


def analyze(diff: str, title: str, summary: ChangeSummary) -> Verdict:
    from .llm import ask_llm, llm_enabled

    baseline = heuristic_verdict(summary)
    if not llm_enabled():
        return baseline
    result = ask_llm(title, diff, summary.categories)
    if result is None:
        return baseline
    score = max(result["risk_score"], baseline.risk_score)
    reasons = result["reasons"] + [r for r in baseline.reasons if r not in result["reasons"]][:2]
    level = RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW
    return Verdict(risk_score=score, level=level, reasons=reasons[:6],
                   summary=summary, source="llm")
