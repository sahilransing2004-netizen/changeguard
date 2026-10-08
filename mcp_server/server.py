import os
import sys
import httpx
from mcp.server.mcpserver import MCPServer

BASE = os.getenv("CHANGEGUARD_URL", "http://localhost:8001")
print(f"[changeguard-mcp] using {BASE}", file=sys.stderr)
mcp = MCPServer("changeguard")


@mcp.tool()
def analyze_diff(diff: str) -> dict:
    """Score a code/config diff as low, medium or high change risk.
    Returns the risk level, score, reasons and related past incidents."""
    try:
        r = httpx.post(f"{BASE}/analyze", json={"diff": diff}, timeout=120)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        return {"error": f"ChangeGuard request to {BASE} failed: {e!r}"}


@mcp.tool()
def recent_verdicts() -> str:
    """Summarise ChangeGuard verdict counts (low/medium/high) from /metrics."""
    try:
        r = httpx.get(f"{BASE}/metrics", timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return f"ChangeGuard request to {BASE} failed: {e!r}"
    lines = [
        l for l in r.text.splitlines()
        if not l.startswith("#") and l.startswith("changeguard_verdicts_total")
    ]
    return "\n".join(lines) or "No verdicts recorded yet."


if __name__ == "__main__":
    mcp.run()
