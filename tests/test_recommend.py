"""The recommendation engine's promises, checked on fixed business profiles."""

import copy

from conftest import HVAC, PIZZA
from shopfloor.catalog import catalog_tools
from shopfloor.engine.pricing import monthly_cost
from shopfloor.engine.recommend import recommend
from shopfloor.models import Business, Metrics

TOOLS = catalog_tools()
BY_ID = {t.id: t for t in TOOLS}


def rec(profile, **changes):
    p = copy.deepcopy(profile)
    for k, v in changes.items():
        if k in Metrics.model_fields:
            p["metrics"][k] = v
        else:
            p[k] = v
    return recommend(Business(**p), TOOLS)


def job(r, name):
    return next(j for j in r["jobs"] if j["job"] == name)


def test_catalog_is_real_and_sourced():
    assert len(TOOLS) >= 15
    for t in TOOLS:
        assert t.pricing.url.startswith("https://"), t.id
        assert t.pricing.quote_only or t.pricing.plans, t.id
        for rv in t.reviews:
            assert rv.url.startswith("https://") and rv.author and rv.quote, (t.id, rv)


def test_never_violates_hard_constraints():
    for profile in (PIZZA, HVAC):
        r = recommend(Business(**profile), TOOLS)
        budget = profile["budget_usd_month"]
        assert r["stack"]["monthly_cost"] <= budget
        for j in r["jobs"]:
            for o in j.get("options", []):
                t = BY_ID[o["tool_id"]]
                assert not t.requires_any or set(t.requires_any) & set(profile["stack"]), o["tool_id"]
                assert o["monthly_cost"] is None or o["monthly_cost"] <= budget


def test_free_builtin_beats_paid_tool_you_dont_need():
    j = job(recommend(Business(**HVAC), TOOLS), "invoice_chasing")
    assert j["status"] == "use_builtin" and j["top"]["tool_id"] == "qbo-reminders"
    paid = next(o for o in j["options"] if o["tool_id"] == "paidnice")
    assert paid["net_monthly"] < j["top"]["net_monthly"]


def test_no_purchase_when_volume_too_low():
    j = job(recommend(Business(**HVAC), TOOLS), "review_replies")
    assert j["status"] == "no_purchase" and j["breakeven"]["needed"] > j["breakeven"]["have"]


def test_low_volume_finds_a_real_free_plan():
    j = job(rec(PIZZA, calls_per_week=8), "missed_calls")
    assert j["top"]["monthly_cost"] == 0 and j["top"]["tool_id"] == "smith-ai"  # Smith.ai Free: 25 calls/mo


def test_missing_data_asks_instead_of_guessing():
    j = job(rec(PIZZA, avg_ticket=None), "missed_calls")
    assert j["status"] == "needs_info" and any(m["field"] == "avg_ticket" for m in j["missing"])


def test_home_services_gets_trade_tools_and_restaurant_tool_is_excluded():
    j = job(recommend(Business(**HVAC), TOOLS), "missed_calls")
    assert j["top"]["tool_id"] == "jobber-receptionist"  # in their stack, confirmed hand-off, cheapest per value
    assert any(d["tool_id"] == "slang-ai" for d in j["disqualified"])
    pizza = job(recommend(Business(**PIZZA), TOOLS), "missed_calls")
    assert any(d["tool_id"] == "jobber-receptionist" for d in pizza["disqualified"])


def test_budget_binding_stack_explains_swaps():
    r = recommend(Business(**PIZZA), TOOLS)
    assert r["stack"]["monthly_cost"] <= 150
    tops = sum(j["top"]["monthly_cost"] for j in r["jobs"] if j.get("top"))
    if tops > 150:
        assert r["stack"]["swaps"]


def test_recommendation_changes_with_the_business():
    small = job(rec(PIZZA, calls_per_week=40), "missed_calls")
    big = job(rec(PIZZA, calls_per_week=600, budget_usd_month=1000), "missed_calls")
    assert small["top"]["monthly_value"] < big["top"]["monthly_value"]


def test_pricing_follows_published_plans():
    goodcall = BY_ID["goodcall"]
    assert monthly_cost(goodcall, {"unique_callers": 80}).usd_month == 79
    assert abs(monthly_cost(goodcall, {"unique_callers": 120}).usd_month - (79 + 20 * 0.79)) < 1e-9
    assert monthly_cost(BY_ID["birdeye"], {}).usd_month is None


def test_every_number_is_explained():
    for j in recommend(Business(**PIZZA), TOOLS)["jobs"]:
        assert j["inputs"] and all({"label", "value", "origin"} <= set(i) for i in j["inputs"])
        for o in j.get("options", []):
            b = o["breakdown"]
            assert abs(sum(b[k]["points"] for k in b) - o["score"]) <= 0.5
