import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp_server import server


class FakeResponse:
    def __init__(self, json_data=None, text=""):
        self._json = json_data
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def test_analyze_diff_returns_service_response(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse({"level": "high", "risk_score": 60})

    monkeypatch.setattr(server.httpx, "post", fake_post)
    result = server.analyze_diff("+ cidr: 0.0.0.0/0")

    assert result["level"] == "high"
    assert captured["url"].endswith("/analyze")
    assert captured["json"] == {"diff": "+ cidr: 0.0.0.0/0"}
