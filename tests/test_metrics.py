from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_exposed_after_analyze():
    client.post("/analyze", json={"diff": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-a\n+b\n", "title": "t"})
    body = client.get("/metrics").text
    assert "changeguard_verdicts_total" in body
    assert "changeguard_analyze_seconds_bucket" in body
