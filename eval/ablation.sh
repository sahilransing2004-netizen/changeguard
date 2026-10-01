#!/usr/bin/env bash
cd ~/changeguard && source .venv/bin/activate
CASES=${1:-eval/cases.json}
run() {
  name=$1; shift
  pkill -f "uvicorn app.main"; sleep 2
  env "$@" uvicorn app.main:app --port 8000 > /tmp/uv.log 2>&1 &
  sleep 5
  echo "=== $name ==="
  python eval/run_eval.py http://localhost:8000/analyze "$CASES"
}
run "heuristic"       CHANGEGUARD_USE_LLM=0 CHANGEGUARD_USE_RAG=0
run "llm + rules"     CHANGEGUARD_USE_LLM=1 CHANGEGUARD_USE_RAG=0
run "llm raw"         CHANGEGUARD_USE_LLM=1 CHANGEGUARD_USE_RAG=0 CHANGEGUARD_LLM_RAW=1
run "llm raw + rag"   CHANGEGUARD_USE_LLM=1 CHANGEGUARD_USE_RAG=1 CHANGEGUARD_LLM_RAW=1
pkill -f "uvicorn app.main"
