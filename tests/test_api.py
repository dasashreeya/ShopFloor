import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

from conftest import PIZZA
from shopfloor.api.app import create_app


def test_owner_flow_over_http(sf):
    c = TestClient(create_app(sf))
    assert c.get("/api/health").json()["tools"] >= 15
    research = c.get("/api/research").json()
    assert research["stats"]["reviews_quoted"] > 20 and research["sba_resources"]

    biz = c.post("/api/businesses", json=PIZZA).json()
    rec = c.get(f"/api/businesses/{biz['id']}/recommendations").json()
    top = next(j for j in rec["jobs"] if j["job"] == "missed_calls")["top"]["tool_id"]

    # an uploaded call log updates the numbers and records where they came from
    rows = [f"2026-10-{d:02d},{'missed' if i < 3 else 'answered'}" for d in range(1, 29) for i in range(20)]
    imp = c.post(f"/api/businesses/{biz['id']}/import/calls", content="date,status\n" + "\n".join(rows),
                 headers={"x-filename": "calls.csv"}).json()
    assert imp["business"]["metric_sources"]["calls_per_week"] == "file: calls.csv"

    base = f"/api/businesses/{biz['id']}/picks"
    pick = c.post(base, json={"tool_id": top, "action": "trial"}).json()
    assert pick["status"] == "trial" and pick["checklist"]
    assert c.post(base, json={"tool_id": top, "action": "trial"}).status_code == 422

    out = c.post(f"{base}/{pick['id']}/checkin", json={"inputs": {"won_from_ai_calls": 10}}).json()
    again = c.post(f"{base}/{pick['id']}/checkin", json={"inputs": {"won_from_ai_calls": 12}}).json()
    assert out["id"] == again["id"]  # re-reporting replaces, never double counts
    acc = c.get("/api/accuracy").json()
    assert acc["reported"] == 1 and acc["eligible"] == 0  # same-day check-in does not calibrate

    other = c.post("/api/businesses", json={**PIZZA, "name": "Someone else"}).json()
    assert c.post(f"/api/businesses/{other['id']}/picks/{pick['id']}/cancel").status_code == 404  # tenant isolation
    bye = c.post(f"{base}/{pick['id']}/cancel").json()
    assert bye["exit_steps"] and bye["pick"]["status"] == "cancelled"


def test_try_tool_is_labeled_simulated(sf):
    c = TestClient(create_app(sf))
    r = c.post("/api/tools/nicejob/try", json={"text": "1 star. Waited an hour."}).json()
    assert r["simulated"] is True and r["reply"]


def test_llm_endpoints_are_rate_limited(sf):
    c = TestClient(create_app(sf, llm_per_hour=2))
    codes = [c.post("/api/tools/nicejob/try", json={"text": "hi"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_all_fail_lab_is_json_safe(sf, monkeypatch):
    from shopfloor.llm import fake
    monkeypatch.setitem(fake._ANSWERS, "lab-judge", lambda u: {"pass": False, "reason": "no"})
    c = TestClient(create_app(sf))
    r = c.post("/api/lab/rosie")
    assert r.status_code == 200 and r.json()["cost_per_resolved_usd"] is None
    assert c.get("/api/catalog").status_code == 200
