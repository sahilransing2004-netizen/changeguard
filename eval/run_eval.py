import json
import sys
import httpx

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/analyze"

cases = json.load(open("eval/cases.json"))
correct = 0
print(f"{'case':<20} {'expected':<9} {'got':<9} {'score':<6} {'source':<10} result")
for c in cases:
    r = httpx.post(URL, json={"diff": c["diff"], "title": c["title"]}, timeout=180)
    r.raise_for_status()
    v = r.json()
    ok = v["level"] == c["expected"]
    correct += ok
    print(f"{c['name']:<20} {c['expected']:<9} {v['level']:<9} {v['risk_score']:<6} {v['source']:<10} {'PASS' if ok else 'FAIL'}")
print(f"\nAccuracy: {correct}/{len(cases)} = {correct / len(cases):.0%}")
