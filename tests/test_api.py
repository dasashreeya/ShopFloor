import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

from shopfloor.api.app import create_app


def test_full_loop_over_http(sf):
    c = TestClient(create_app(sf))
    assert c.get("/api/health").json()["tools"] == 6

    lab = c.post("/api/lab/ringback").json()
    assert lab["n_tasks"] == 5 and 0 <= lab["accuracy"] <= 1

    biz = c.post("/api/businesses", json={"name": "Luna Taqueria"}).json()
    deck = c.get(f"/api/businesses/{biz['id']}/deck").json()
    assert deck, "expected at least one card"
    nets = [d["monthly_value_usd"] - d["monthly_cost_usd"] for d in deck]
    assert nets == sorted(nets, reverse=True)
    ringback = next(d for d in deck if d["tool_id"] == "ringback")
    assert ringback["lab_accuracy"] == lab["accuracy"]

    hire = c.post(f"/api/cards/{ringback['id']}/swipe", json={"direction": "right"}).json()["hire"]
    outcome = c.post(f"/api/hires/{hire['id']}/measure").json()
    assert outcome["actual_monthly_usd"] > 0
    [acc] = c.get("/api/accuracy").json()
    assert acc["job"] == "missed_calls" and acc["verified_hires"] == 1

    assert c.post(f"/api/hires/{hire['id']}/fire").json()["billing"]["status"] == "cancelled"
    assert c.post(f"/api/hires/{hire['id']}/measure").status_code == 409


def test_errors_are_clean(sf):
    c = TestClient(create_app(sf))
    assert c.get("/api/businesses/nope/deck").status_code == 404
    assert c.post("/api/lab/unstructured-demo").status_code == 422
    assert c.post("/api/cards/x/swipe", json={"direction": "sideways"}).status_code == 422


def test_ui_support_endpoints(sf):
    c = TestClient(create_app(sf))
    biz = c.post("/api/businesses", json={"name": "Joe's Pizza"}).json()
    assert c.get(f"/api/businesses/{biz['id']}").json()["name"] == "Joe's Pizza"
    deck = c.get(f"/api/businesses/{biz['id']}/deck").json()
    rb = next(d for d in deck if d["tool_id"] == "ringback")
    assert [s["label"] for s in rb["stats"]] == ["Missed during rush", "Recoverable orders"]

    rep = c.get(f"/api/businesses/{biz['id']}/tools/ringback/replay").json()
    assert len(rep["hourly"]) == 24 and sum(rep["hourly"]) == rep["actions"] > 0
    assert 11 <= rep["peak_hour"] <= 13  # the lunch rush

    assert c.get(f"/api/businesses/{biz['id']}/roster").json() == []
    c.post(f"/api/cards/{rb['id']}/swipe", json={"direction": "up"})
    [row] = c.get(f"/api/businesses/{biz['id']}/roster").json()
    assert row["hire"]["status"] == "shadow" and row["hire"]["shadow_actions"] > 0
    assert row["tool"]["name"] == "RingBack" and row["prediction"]["tool_id"] == "ringback"
    assert row["outcome"] is None and "shadow_log" not in row["hire"]
    assert c.get("/api/businesses/nope/roster").status_code == 404
