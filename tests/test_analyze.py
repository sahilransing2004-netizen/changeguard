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
