"""The recommendation engine.

Per job:
  1. Estimate the job's monthly value from the owner's numbers (estimators.py). Missing data -> ask, don't guess.
  2. Hard constraints remove tools, each with a stated reason: industry fit, required software, budget,
     must-have capabilities (Spanish, human hand-off).
  3. Each surviving tool gets a cost for *this* business's volume (pricing.py) and a tool-specific value
     (e.g. a paid tool on top of a free built-in you already have only gets the incremental share).
  4. Score = Value for you (40) + Fit (25) + Customer evidence (20) + Transparency (15). Every point is explained.
  5. Outcome per job is one of: use_builtin (free thing you already own), recommend, no_purchase (nothing pays
     for itself at your volume, with the break-even shown), needs_info.
Across jobs, a budget-aware stack is assembled (cheapest-to-value first, never over budget).
"""

import itertools
import math

from shopfloor.catalog import assumption, industry_group
from shopfloor.engine.estimators import ESTIMATORS, JobEstimate
from shopfloor.engine.pricing import monthly_cost
from shopfloor.models import Business, Job, Tool

JOB_LABELS = {
    Job.MISSED_CALLS: "Answer missed calls",
    Job.REVIEW_REPLIES: "Reply to online reviews",
    Job.INVOICE_CHASING: "Chase late invoices",
    Job.EMAIL_TRIAGE: "Tame the inbox",
}
PRIOR_MEAN, PRIOR_WEIGHT = 3.0, 25
ROI_CAP = 20.0
NEEDS_BY_JOB = {Job.MISSED_CALLS: ("spanish", "human_handoff")}  # must-haves only apply where they mean something
LOW_RELEVANCE_WEIGHT = 0.25  # ratings mostly about a different product (e.g. human receptionists)  # Bayesian shrinkage for star ratings: few reviews -> near 3.0


def evidence(tool: Tool) -> dict:
    """Customer-evidence score (0-20) from independent ratings, shrunk toward 3.0 when samples are small."""
    rated = [r for r in tool.ratings if r.score is not None and r.count > 0]
    w = {id(r): (LOW_RELEVANCE_WEIGHT if r.relevance == "low" else 1.0) for r in rated}
    n = sum(r.count for r in rated)
    eff = sum(r.count * w[id(r)] for r in rated)
    weighted = sum(r.score * r.count * w[id(r)] for r in rated)
    adj = (weighted + PRIOR_MEAN * PRIOR_WEIGHT) / (eff + PRIOR_WEIGHT)
    pts = 20 * (adj - 1) / 4
    relevant = [rv for rv in tool.reviews if rv.relevant]
    critical = [rv for rv in relevant if (rv.stars or 5) <= 2]
    marketplace = any("App Store" in r.platform for r in rated)
    label = "thin" if n < 20 else "moderate" if n < 200 else "strong"
    notes = []
    if n == 0:
        notes.append("No independent ratings found: scored as neutral, not as good.")
    if any(r.relevance == "low" for r in rated):
        notes.append("Platform rating mostly reflects a different product: counted at 25% weight.")
    if marketplace:
        notes.append("Marketplace ratings (e.g. Xero App Store) skew positive.")
    if any(not rv.relevant for rv in tool.reviews):
        notes.append(f"{sum(not rv.relevant for rv in tool.reviews)} review(s) excluded as not about this product.")
    return {"points": round(pts, 1), "adjusted_stars": round(adj, 2), "ratings_count": n, "strength": label,
            "critical_reviews": len(critical), "relevant_reviews": len(relevant), "notes": notes}


def transparency(tool: Tool) -> dict:
    p, pts, why = tool.pricing, 0.0, []
    if p.quote_only or not p.plans:
        why.append("Price only by quote (0/8)")
    elif p.evidence in ("vendor_page", "vendor_help_center"):
        pts += 8; why.append("Price published by the vendor (8/8)")
    else:
        pts += 4; why.append("Price only from a third-party listing (4/8)")
    t = (p.trial or "").lower()
    if t and not any(w in t for w in ("not stated", "not verified", "demo only")):
        pts += 4; why.append("Free trial or free plan (4/4)")
    else:
        why.append("No stated free trial (0/4)")
    c = (p.contract or "").lower()
    if any(w in c for w in ("cancel anytime", "month-to-month", "no contracts", "none", "monthly")):
        pts += 3; why.append("Month-to-month / cancel anytime (3/3)")
    else:
        why.append("Contract terms unclear (0/3)")
    return {"points": pts, "why": why}


def _value_points(value: float, cost: float | None) -> tuple[float, str]:
    """40 points on a log scale of value/price, so $87 vs $222 for the same job still matters."""
    if cost is None:
        return 0.0, "Can't compute: no published price"
    net = value - cost
    if net <= 0:
        return 0.0, f"Costs more than it's likely worth to you (net ${net:,.0f}/mo)"
    roi = value / cost if cost > 0 else ROI_CAP
    pts = 40 * min(1.0, math.log1p(roi) / math.log1p(ROI_CAP))
    return round(pts, 1), (f"Worth ~{roi:.1f}x its price to you" if cost > 0 else "Free and worth it")


def _constraints(tool: Tool, biz: Business) -> list[str]:
    reasons = []
    group = industry_group(biz.industry)
    if "all" not in tool.verticals and group not in tool.verticals:
        reasons.append(f"Built for {', '.join(tool.verticals).replace('_', ' ')}, not your industry")
    stack = set(biz.stack)
    if tool.requires_any and not stack & set(tool.requires_any):
        reasons.append(f"Needs {' or '.join(tool.requires_any).replace('_', ' ')}, which you don't use")
    for need in NEEDS_BY_JOB.get(tool.jobs[0], ()):
        if biz.needs.get(need) and tool.capabilities.get(need) is False:
            reasons.append(f"No {need.replace('_', ' ')}")
    return reasons


def _builtin_available(tools: list[Tool], job: Job, biz: Business) -> list[Tool]:
    return [t for t in tools if t.kind == "builtin" and job in t.jobs and not _constraints(t, biz)]


def _tool_value(tool: Tool, est: JobEstimate, biz: Business, builtins: list[Tool]) -> tuple[float, float, float, list[str]]:
    """Adjust the job value for this specific tool. Returns low, mid, high, notes."""
    k, notes = 1.0, []
    caps = tool.capabilities
    if est.job == Job.EMAIL_TRIAGE:
        if caps.get("drafts_replies") is False:
            k *= 0.6; notes.append("Sorts only, no reply drafts: counted at 60% (assumption)")
        elif caps.get("sorts_inbox") is False:
            k *= 0.5; notes.append("Drafts but doesn't sort: counted at 50% (assumption)")
    if tool.kind == "builtin":
        if est.job == Job.REVIEW_REPLIES and not tool.baseline_saves_time:
            # Doing it yourself gets the rating effect but costs your time instead of saving it.
            gap = 1 - (biz.metrics.reply_share or 0.0)
            diy_time = est.time_component * gap  # replies you'd now write yourself
            return (0.0, max(0.0, est.mid - est.time_component - diy_time),
                    max(0.0, est.high - est.time_component - diy_time),
                    ["Free, but you write every reply yourself: your time is subtracted"])
        if est.job == Job.INVOICE_CHASING and biz.metrics.uses_builtin_reminders:
            return 0.0, 0.0, 0.0, ["You already use this"]
        return est.low * k, est.mid * k, est.high * k, notes
    if builtins and tool.kind != "builtin" and est.job in (Job.INVOICE_CHASING, Job.EMAIL_TRIAGE):
        inc = assumption("builtin_incremental_share")
        notes.append(f"You already have {builtins[0].name} for free: only the extra {inc['mid']:.0%} is counted (assumption)")
        return est.low * inc["low"] * k, est.mid * inc["mid"] * k, est.high * inc["high"] * k, notes
    return est.low * k, est.mid * k, est.high * k, notes


def score_tool(tool: Tool, est: JobEstimate, biz: Business, builtins: list[Tool], lab: dict | None = None) -> dict:
    low, mid, high, value_notes = _tool_value(tool, est, biz, builtins)
    cost = monthly_cost(tool, est.usage)
    vpts, vwhy = _value_points(mid, cost.usd_month)
    stack = set(biz.stack)
    fit, fit_why = 0.0, []
    group = industry_group(biz.industry)
    if group in tool.verticals:
        fit += 10; fit_why.append("Made for your industry (10/10)")
    else:
        fit += 7; fit_why.append("General-purpose (7/10)")
    overlap = sorted(stack & set(tool.works_with))
    if tool.requires_any or overlap:
        fit += 10; fit_why.append(f"Connects to {', '.join(overlap) or 'your stack'} (10/10)")
    else:
        fit += 6; fit_why.append("Works standalone; no direct link to your software (6/10)")
    need_pts, unconfirmed = 5.0, []
    for need in NEEDS_BY_JOB.get(est.job, ()):
        if biz.needs.get(need):
            v = tool.capabilities.get(need)
            if v is None:
                need_pts = 0.0; unconfirmed.append(need.replace("_", " "))
    fit += need_pts
    fit_why.append(f"Your must-haves: {'unconfirmed: ' + ', '.join(unconfirmed) if unconfirmed else 'met'} ({need_pts:g}/5)")
    ev, tr = evidence(tool), transparency(tool)
    total = vpts + fit + ev["points"] + tr["points"]
    return {
        "tool_id": tool.id, "name": tool.name, "vendor": tool.vendor, "kind": tool.kind,
        "score": round(total), "monthly_value_low": round(low), "monthly_value": round(mid), "monthly_value_high": round(high),
        "monthly_cost": None if cost.usd_month is None else round(cost.usd_month, 2), "plan": cost.plan, "cost_note": cost.note,
        "net_monthly": None if cost.usd_month is None else round(mid - cost.usd_month),
        "breakdown": {
            "value": {"points": vpts, "max": 40, "why": [vwhy, *value_notes]},
            "fit": {"points": fit, "max": 25, "why": fit_why},
            "evidence": {"points": ev["points"], "max": 20, "why": [f"{ev['adjusted_stars']}★ adjusted from {ev['ratings_count']} ratings ({ev['strength']} evidence)", *ev["notes"]]},
            "transparency": {"points": tr["points"], "max": 15, "why": tr["why"]},
        },
        "evidence": ev, "unconfirmed_needs": unconfirmed,
        "trial": tool.pricing.trial, "contract": tool.pricing.contract,
        "lab": lab,
    }


def recommend_job(job: Job, biz: Business, tools: list[Tool], labs: dict[str, dict] | None = None) -> dict:
    labs = labs or {}
    est = ESTIMATORS[job](biz)
    cands = [t for t in tools if job in t.jobs and t.kind != "candidate"]
    out = {"job": job.value, "label": JOB_LABELS[job], "facts": est.facts, "inputs": est.inputs,
           "missing": est.missing, "opportunity": round(est.opportunity, 1), "opportunity_label": est.opportunity_label,
           "is_pain": job in biz.pains}
    if not est.ok:
        out.update(status="needs_info", options=[], disqualified=[], headline="Tell us a bit more to estimate this.")
        return out
    disq, eligible = [], []
    for t in cands:
        reasons = _constraints(t, biz)
        (disq.append({"tool_id": t.id, "name": t.name, "reasons": reasons}) if reasons else eligible.append(t))
    builtins = _builtin_available(eligible, job, biz)
    options = [score_tool(t, est, biz, builtins, labs.get(t.id)) for t in eligible]
    if biz.budget_usd_month is not None:
        keep = []
        for o in options:
            if o["monthly_cost"] is not None and o["monthly_cost"] > biz.budget_usd_month:
                disq.append({"tool_id": o["tool_id"], "name": o["name"],
                             "reasons": [f"${o['monthly_cost']:,.0f}/mo is over your ${biz.budget_usd_month:,.0f} budget"]})
            else:
                keep.append(o)
        options = keep
    options.sort(key=lambda o: (o["net_monthly"] is not None and o["net_monthly"] > 0, o["score"], o["net_monthly"] or -1e9), reverse=True)
    out["options"], out["disqualified"] = options, disq
    paying = [o for o in options if o["net_monthly"] is not None and o["net_monthly"] > 0]
    top = paying[0] if paying else None
    if top and top["kind"] == "builtin":
        out["status"] = "use_builtin"
        out["headline"] = f"Turn on {top['name']} first. It's free and you already have it."
    elif top:
        out["status"] = "recommend"
        out["headline"] = f"{top['name']}: about ${top['monthly_value']:,}/mo of value for ${top['monthly_cost']:,.0f}/mo."
    else:
        out["status"] = "no_purchase"
        cheapest = min((o for o in options if o["monthly_cost"]), key=lambda o: o["monthly_cost"], default=None)
        if cheapest and est.unit_value > 0:
            need = cheapest["monthly_cost"] / est.unit_value
            out["breakeven"] = {"tool": cheapest["name"], "cost": cheapest["monthly_cost"], "needed": round(need, 1),
                                "have": round(est.opportunity, 1), "unit": est.opportunity_label}
            out["headline"] = (f"Don't buy yet. The cheapest option ({cheapest['name']}, ${cheapest['monthly_cost']:,.0f}/mo) "
                               f"pays off at ~{math.ceil(need)} {est.opportunity_label}; you have ~{est.opportunity:,.0f}.")
        else:
            out["headline"] = "Nothing here pays for itself for you right now."
    out["top"] = top
    return out


def build_stack(results: list[dict], budget: float | None) -> dict:
    """Best combination of at most one tool per job that maximizes total net value within budget.

    Exhaustive search over each job's paying options (a handful per job), so the stack can swap a job's top pick
    for a cheaper option when that frees budget for another job.
    """
    menus = [[None] + [o for o in r.get("options", []) if o["net_monthly"] is not None and o["net_monthly"] > 0]
             for r in results if r["status"] in ("recommend", "use_builtin")]
    best, best_key = (), (0.0, 0)
    top_picks = tuple(r["top"] for r in results if r.get("top"))
    if budget is None or sum(o["monthly_cost"] for o in top_picks) <= budget:
        menus = [[o] for o in top_picks]  # budget isn't binding: keep each job's best-scored pick
    for combo in itertools.product(*menus):
        chosen = [o for o in combo if o]
        cost = sum(o["monthly_cost"] for o in chosen)
        if budget is not None and cost > budget + 1e-9:
            continue
        key = (sum(o["net_monthly"] for o in chosen), -len(chosen))
        if key > best_key:
            best, best_key = tuple(chosen), key
    tops = {r["job"]: r["top"]["tool_id"] for r in results if r.get("top")}
    swaps = []
    for r in results:
        if not r.get("top"):
            continue
        mine = next((o for o in best if o["tool_id"] in {x["tool_id"] for x in r.get("options", [])}), None)
        if mine is None:
            swaps.append(f"{r['label']}: skipped to stay within budget (top pick {r['top']['name']})")
        elif mine["tool_id"] != tops[r["job"]]:
            swaps.append(f"{r['label']}: {mine['name']} instead of {r['top']['name']} to fit the budget")
    spent = sum(o["monthly_cost"] for o in best)
    value = sum(o["monthly_value"] for o in best)
    return {"tools": [{"tool_id": o["tool_id"], "name": o["name"], "monthly_cost": o["monthly_cost"], "monthly_value": o["monthly_value"]} for o in best],
            "swaps": swaps, "monthly_cost": round(spent, 2), "monthly_value": round(value), "net_monthly": round(value - spent),
            "budget": budget,
            "note": "One tool per job, so values add up without double counting. Chosen to maximize total net value within your budget."}


def recommend(biz: Business, tools: list[Tool], labs: dict[str, dict] | None = None) -> dict:
    order = sorted(ESTIMATORS, key=lambda j: j not in biz.pains)
    results = [recommend_job(j, biz, tools, labs) for j in order]
    rank = {"recommend": 0, "use_builtin": 1, "no_purchase": 2, "needs_info": 3}
    results.sort(key=lambda r: (not r["is_pain"], rank[r["status"]], -((r.get("top") or {}).get("net_monthly") or 0)))
    return {"business_id": biz.id, "revision": biz.revision, "jobs": results, "stack": build_stack(results, biz.budget_usd_month)}
