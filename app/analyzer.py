import re

from .models import ChangeSummary, Verdict, RiskLevel

BASE_WEIGHTS = {"terraform": 30, "database": 30, "kubernetes": 20,
                "config": 15, "ci": 10, "docker": 10, "app": 5}

DESTRUCTIVE_PATTERNS = [
    r"\bDROP\s+(TABLE|COLUMN|DATABASE|INDEX)\b",
    r"\bTRUNCATE\b",
    r"\bDELETE\s+FROM\b",
    r"terraform\s+destroy",
    r"replicas:\s*0\b",
    r"\bkubectl\s+delete\b",
]

# (reason, "+" added / "-" removed line, file-path regex or None, line regex, minimum score)
RISK_RULES = [
    ("Opens network access to the whole internet (0.0.0.0/0 or ::/0)", "+", None,
     r"0\.0\.0\.0/0|::/0", 60),
    ("Wildcard IAM action (e.g. s3:*)", "+", None,
     r"""["'][a-z0-9-]+:\*["']|\bactions?\b["']?\s*[=:]\s*\[?\s*["']\*["']""", 60),
    ("Wildcard IAM resource", "+", None,
     r"""\bresources?\b["']?\s*[=:]\s*\[?\s*["']\*["']""", 40),
    ("Removes a Terraform resource", "-", r"\.tf$",
     r'^\s*resource\s+"', 60),
    ("Removes a topic or queue definition", "-", r"topic|queue|stream",
     r"^\s*-?\s*(name|topic)\s*:", 60),
    ("Removes a Kubernetes workload, volume or network policy", "-", r"\.ya?ml$",
     r"^\s*kind:\s*(Deployment|StatefulSet|PersistentVolumeClaim|Namespace|NetworkPolicy)\b", 60),
    ("Makes a storage bucket publicly readable or writable", "+", r"\.tf$",
     r"""\bacl\b["']?\s*[=:]\s*["']public-read(-write)?["']""", 60),
    ("Runs a container in privileged mode", "+", r"\.ya?ml$",
     r"^\s*privileged:\s*true\b", 60),
    ("Disables database backups", "+", None,
     r"\bbackup_retention_period\b\s*[=:]\s*0\b", 60),
    ("Hardcoded credential", "+", r"^(?!tests?/)",
     r"""(api[_-]?key|secret|password|token)\w*["']?\s*[=:]\s*["'](?![$]|\{\{)[^"'\s]{12,}["']|sk_live_\w+|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----""", 60),
]


def find_destructive(diff: str) -> list[str]:
    added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    text = "\n".join(added)
    return [p for p in DESTRUCTIVE_PATTERNS if re.search(p, text, flags=re.I)]


def iter_changed_lines(diff: str):
    """Yield (path, sign, text) for each added/removed line, tracking the current file."""
    path = ""
    for line in diff.splitlines():
        m = re.match(r"diff --git a/(\S+) b/(\S+)", line)
        if m:
            path = m.group(2)
        elif line.startswith(("--- a/", "--- /dev/null", "+++ b/", "+++ /dev/null")):
            continue
        elif line.startswith("+"):
            yield path, "+", line[1:]
        elif line.startswith("-"):
            yield path, "-", line[1:]


def find_risky(diff: str) -> list[tuple[str, int]]:
    hits: dict[str, int] = {}
    for path, sign, text in iter_changed_lines(diff):
        for reason, rsign, path_re, line_re, floor in RISK_RULES:
            if sign != rsign:
                continue
            if path_re and not re.search(path_re, path, flags=re.I):
                continue
            if re.search(line_re, text, flags=re.I):
                hits[reason] = floor
    return list(hits.items())


COMMENT_PREFIXES = ("#", "//", "--", "/*", "*", "<!--")


def is_comment_only(diff: str) -> bool:
    """True if the diff changes at least one line and every changed line is blank or a comment."""
    seen = False
    for _, _, text in iter_changed_lines(diff):
        t = text.strip()
        if not t:
            continue
        seen = True
        if not t.startswith(COMMENT_PREFIXES):
            return False
    return seen


def is_trivial(diff: str) -> bool:
    """Comment/whitespace-only change with no risky pattern (a secret in a comment still counts)."""
    return bool(diff) and is_comment_only(diff) and not find_risky(diff)


def heuristic_verdict(summary: ChangeSummary, diff: str = "") -> Verdict:
    if is_trivial(diff):
        return Verdict(risk_score=5, level=RiskLevel.LOW,
                       reasons=["Only comments or whitespace changed",
                                f"{summary.added} lines added, {summary.removed} removed"],
                       summary=summary)
    score = sum(BASE_WEIGHTS.get(c, 5) for c in summary.categories)
    score += min((summary.added + summary.removed) // 20, 20)
    destructive = find_destructive(diff)
    if destructive:
        score = max(score, 70)
    risky = find_risky(diff)
    for _, floor in risky:
        score = max(score, floor)
    score = min(score, 100)
    level = RiskLevel.HIGH if score >= 60 else RiskLevel.MEDIUM if score >= 30 else RiskLevel.LOW
    reasons = [f"Touches {c} files" for c in summary.categories]
    if destructive:
        reasons.insert(0, "Contains destructive operation (drop/delete/truncate/destroy)")
    reasons = [f"Risky pattern: {r}" for r, _ in risky] + reasons
    reasons.append(f"{summary.added} lines added, {summary.removed} removed")
    return Verdict(risk_score=score, level=level, reasons=reasons, summary=summary)


def analyze(diff: str, title: str, summary: ChangeSummary) -> Verdict:
    from . import rag
    from .llm import ask_llm, llm_enabled

    baseline = heuristic_verdict(summary, diff)
    if not llm_enabled() or is_trivial(diff):
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
