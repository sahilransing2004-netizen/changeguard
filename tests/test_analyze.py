from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

TF_DIFF = """diff --git a/infra/main.tf b/infra/main.tf
--- a/infra/main.tf
+++ b/infra/main.tf
@@ -1,2 +1,2 @@
-instance_type = "t3.micro"
+instance_type = "t3.large"
"""

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_terraform_change_is_flagged():
    r = client.post("/analyze", json={"diff": TF_DIFF})
    assert r.status_code == 200
    body = r.json()
    assert "terraform" in body["summary"]["categories"]
    assert body["risk_score"] >= 30


def test_llm_result_is_used(monkeypatch):
    monkeypatch.setenv("CHANGEGUARD_USE_LLM", "1")
    monkeypatch.setattr("app.llm.ask_llm",
                        lambda t, d, c: {"risk_score": 82, "reasons": ["Instance resize may restart the host"]})
    body = client.post("/analyze", json={"diff": TF_DIFF}).json()
    assert body["source"] == "llm"
    assert body["level"] == "high"


def test_falls_back_when_llm_fails(monkeypatch):
    monkeypatch.setenv("CHANGEGUARD_USE_LLM", "1")
    monkeypatch.setattr("app.llm.ask_llm", lambda t, d, c: None)
    body = client.post("/analyze", json={"diff": TF_DIFF}).json()
    assert body["source"] == "heuristic"


def test_llm_cannot_score_below_heuristic(monkeypatch):
    monkeypatch.setenv("CHANGEGUARD_USE_LLM", "1")
    monkeypatch.setattr("app.llm.ask_llm", lambda t, d, c: {"risk_score": 0, "reasons": ["looks fine"]})
    body = client.post("/analyze", json={"diff": TF_DIFF}).json()
    assert body["risk_score"] >= 30
