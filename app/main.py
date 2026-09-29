from fastapi import FastAPI
from .models import AnalyzeRequest, Verdict
from .diff_parser import parse_diff
from .analyzer import heuristic_verdict

app = FastAPI(title="ChangeGuard", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    summary = parse_diff(req.diff)
    return heuristic_verdict(summary)
