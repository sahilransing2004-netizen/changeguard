import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_PROVIDER"] = "none"   # CI has no Ollama: heuristic mode
from app.diff_parser import parse_diff
from app.analyzer import analyze

diff = sys.stdin.read()
v = analyze(diff, os.getenv("PR_TITLE", ""), parse_diff(diff))
data = v.model_dump(mode="json")
json.dump(data, open("verdict.json", "w"), indent=2)

icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}[data["level"]]
lines = [f"## {icon} ChangeGuard: {data['level'].upper()} risk ({data['risk_score']}/100)", ""]
lines += [f"- {r}" for r in data["reasons"]]
open("comment.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
