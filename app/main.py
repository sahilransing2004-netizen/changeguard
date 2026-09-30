import time
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from .models import AnalyzeRequest, Verdict
from .diff_parser import parse_diff
from .analyzer import analyze as run_analysis

app = FastAPI(title="ChangeGuard", version="0.3.0")

VERDICTS = Counter("changeguard_verdicts_total", "Verdicts issued", ["level", "source"])
RISK = Histogram("changeguard_risk_score", "Risk score of analyzed changes",
                 buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
LATENCY = Histogram("changeguard_analyze_seconds", "Analysis latency in seconds",
                    buckets=[0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60])


@app.get("/")
def root():
    return {"service": "ChangeGuard", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    start = time.perf_counter()
    summary = parse_diff(req.diff)
    v = run_analysis(req.diff, req.title, summary)
    LATENCY.observe(time.perf_counter() - start)
    RISK.observe(v.risk_score)
    VERDICTS.labels(level=getattr(v.level, "value", str(v.level)), source=str(v.source)).inc()
    return v
