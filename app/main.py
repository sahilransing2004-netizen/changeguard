from fastapi import FastAPI
from .models import AnalyzeRequest, Verdict
from .diff_parser import parse_diff
from .analyzer import analyze as run_analysis

app = FastAPI(title="ChangeGuard", version="0.2.0")


@app.get("/")
def root():
    return {"service": "ChangeGuard", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    summary = parse_diff(req.diff)
    return run_analysis(req.diff, req.title, summary)
