"""Evaluate the recommender against two naive baselines on fixed business personas.

Personas are evaluation fixtures (plausible owner inputs written before tuning), not real businesses.
Baselines mimic what an owner gets from a review site or a quick search:
  - "Top-rated": per job, the tool with the highest star rating (review-site style)
  - "Cheapest": per job, the lowest advertised entry price
We count recommendations that break a hard rule the owner gave us, or that lose money for them by our own math.

Run: uv run python scripts/evaluate.py  (writes docs/EVALUATION.md)
"""

from pathlib import Path

from shopfloor.catalog import catalog_tools, industry_group
from shopfloor.engine.estimators import ESTIMATORS
from shopfloor.engine.pricing import monthly_cost
from shopfloor.engine.recommend import _builtin_available, _constraints, _tool_value, recommend
from shopfloor.models import Business

M = dict
PERSONAS = [
    ("Busy pizzeria, Square + QuickBooks, $150 budget", dict(industry="restaurant", stack=["square", "google_business", "gmail", "quickbooks"], budget_usd_month=150,
        metrics=M(calls_per_week=180, missed_share=0.25, avg_ticket=32, reviews_per_month=25, reply_share=0.1, monthly_revenue=60000, invoices_per_month=6, avg_invoice=450, email_hours_per_week=4))),
    ("Tiny café, Square only, $40 budget", dict(industry="cafe", stack=["square", "google_business"], budget_usd_month=40,
        metrics=M(calls_per_week=15, missed_share=0.3, avg_ticket=9, reviews_per_month=10, reply_share=0.0, monthly_revenue=18000))),
    ("Restaurant with OpenTable, Spanish required", dict(industry="restaurant", stack=["toast", "opentable", "google_business", "gmail"], budget_usd_month=600, needs={"spanish": True},
        metrics=M(calls_per_week=300, missed_share=0.35, avg_ticket=58, reviews_per_month=40, reply_share=0.3, monthly_revenue=140000))),
    ("HVAC on Jobber, needs human hand-off", dict(industry="hvac", stack=["jobber", "quickbooks", "google_business", "google_workspace", "gmail"], budget_usd_month=300, needs={"human_handoff": True},
        metrics=M(calls_per_week=60, reviews_per_month=8, invoices_per_month=70, avg_invoice=620, late_share=0.35, email_hours_per_week=6, owner_hourly_value=45, uses_builtin_reminders=False))),
    ("Plumber, no field software, Xero", dict(industry="plumbing", stack=["xero", "gmail", "google_business"], budget_usd_month=200,
        metrics=M(calls_per_week=40, missed_share=0.45, invoices_per_month=45, avg_invoice=380, late_share=0.4, email_hours_per_week=5))),
    ("Landscaper, seasonal, already uses QuickBooks reminders", dict(industry="landscaping", stack=["quickbooks", "gmail"], budget_usd_month=100,
        metrics=M(calls_per_week=35, avg_ticket=220, invoices_per_month=90, avg_invoice=180, late_share=0.25, uses_builtin_reminders=True))),
    ("Salon, Square, Spanish, $60 budget", dict(industry="salon", stack=["square", "google_business", "gmail"], budget_usd_month=60, needs={"spanish": True},
        metrics=M(calls_per_week=50, missed_share=0.3, avg_ticket=85, reviews_per_month=6, reply_share=0.5, email_hours_per_week=2))),
    ("Retail shop, Outlook, inbox-heavy", dict(industry="retail", stack=["clover", "outlook", "google_business"], budget_usd_month=80,
        metrics=M(calls_per_week=20, missed_share=0.2, avg_ticket=40, reviews_per_month=5, email_hours_per_week=10, email_users=2))),
    ("Cleaning company, Google Workspace, no budget limit", dict(industry="cleaning", stack=["google_workspace", "gmail", "quickbooks", "google_business"], budget_usd_month=None,
        metrics=M(calls_per_week=25, missed_share=0.5, avg_ticket=160, invoices_per_month=60, avg_invoice=160, late_share=0.2, email_hours_per_week=7))),
    ("Auto repair, low call volume", dict(industry="auto_repair", stack=["quickbooks", "google_business", "gmail"], budget_usd_month=100,
        metrics=M(calls_per_week=6, missed_share=0.2, avg_ticket=300, reviews_per_month=3))),
    ("Food truck, phone only, numbers unknown", dict(industry="food_truck", stack=["square"], budget_usd_month=50, metrics=M())),
]

TOOLS = catalog_tools()


def violations(tool, biz, cost) -> list[str]:
    v = list(_constraints(tool, biz))
    if biz.budget_usd_month is not None and cost is not None and cost > biz.budget_usd_month:
        v.append("over budget")
    return v


def baseline(biz: Business, how: str) -> dict:
    picks = {}
    for job, est_fn in ESTIMATORS.items():
        est = est_fn(biz)
        cands = [t for t in TOOLS if job in t.jobs and t.kind != "builtin"]
        if how == "rated":
            pick = max(cands, key=lambda t: max([r.score or 0 for r in t.ratings] or [0]))
        else:
            pick = min(cands, key=lambda t: min([p.usd_month for p in t.pricing.plans if p.usd_month > 0] or [1e9]))
        cost = monthly_cost(pick, est.usage).usd_month if est.ok else None
        builtins = _builtin_available(TOOLS, job, biz)
        _, mid, _, _ = _tool_value(pick, est, biz, builtins) if est.ok else (0, None, 0, [])
        picks[job.value] = {"tool": pick.name, "cost": cost, "net": None if (mid is None or cost is None) else mid - cost,
                            "violations": violations(pick, biz, cost), "free_alternative_ignored": bool(builtins) and not biz.metrics.uses_builtin_reminders,
                            "asked_for_missing_data": False if est.ok else None}
    return picks


def main():
    rows, totals = [], {k: {"violations": 0, "losing": 0, "free_ignored": 0, "guessed": 0, "n": 0} for k in ("ShopFloor", "Top-rated", "Cheapest")}
    for name, p in PERSONAS:
        biz = Business(name=name, **p)
        rec = recommend(biz, TOOLS)
        sf = {}
        for j in rec["jobs"]:
            top = j.get("top")
            sf[j["job"]] = {"tool": top["name"] if top else {"no_purchase": "Don't buy (break-even shown)", "needs_info": "Asks for missing numbers"}[j["status"]],
                            "status": j["status"]}
            t = totals["ShopFloor"]; t["n"] += 1
            if top:
                tool = next(x for x in TOOLS if x.id == top["tool_id"])
                t["violations"] += bool(violations(tool, biz, top["monthly_cost"]))
                t["losing"] += (top["net_monthly"] or 0) <= 0
        for label, how in (("Top-rated", "rated"), ("Cheapest", "cheap")):
            for job, b in baseline(biz, how).items():
                t = totals[label]; t["n"] += 1
                t["violations"] += bool(b["violations"])
                t["losing"] += b["net"] is not None and b["net"] <= 0
                t["free_ignored"] += b["free_alternative_ignored"]
                t["guessed"] += b["asked_for_missing_data"] is None
        rows.append((name, sf, baseline(biz, "rated")))

    out = ["# Recommendation evaluation", "",
           "Generated by `scripts/evaluate.py`. **Personas are evaluation fixtures** (plausible owner inputs, written before tuning), not real businesses. "
           "Tool data is the real catalog in `shopfloor/catalog/tools.json`.", "",
           f"{len(PERSONAS)} personas × 4 jobs = {len(PERSONAS) * 4} recommendations per method.", "",
           "| Method | Breaks an owner's hard rule (software, industry, budget, must-have) | Recommends a purchase that loses money (by our own estimate) | Ignores a free built-in the owner already has | Recommends without the data to justify it |",
           "|---|---|---|---|---|"]
    for k, t in totals.items():
        out.append(f"| {k} | {t['violations']} / {t['n']} | {t['losing']} / {t['n']} | {t['free_ignored']} / {t['n']} | {t['guessed']} / {t['n']} |")
    out += ["", "ShopFloor's zeros hold by construction: hard rules run before scoring and 'don't buy' and 'need data' are allowed answers. "
            "The baselines show how often a ratings-first or price-first choice would mislead these owners.", "",
            "Limits: value is judged by our own estimator, so 'loses money' is relative to our assumptions (see Research). "
            "The real test is the 16-week pilot: owner check-ins against these predictions.", "", "## Per persona", ""]
    for name, sf, rated in rows:
        out.append(f"### {name}")
        out.append("| Job | ShopFloor | Top-rated baseline |")
        out.append("|---|---|---|")
        for job in sf:
            b = rated[job]
            flag = f" ⚠️ {', '.join(b['violations'])}" if b["violations"] else ""
            flag += " ⚠️ loses money" if b["net"] is not None and b["net"] <= 0 else ""
            out.append(f"| {job.replace('_', ' ')} | {sf[job]['tool']} | {b['tool']}{flag} |")
        out.append("")
    Path("docs/EVALUATION.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:12]))


if __name__ == "__main__":
    main()
