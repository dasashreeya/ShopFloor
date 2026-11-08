"""Monthly value of doing a job well, from the owner's own numbers plus sourced, labeled assumptions.

Rules:
- LLMs never compute money. This is plain arithmetic with every input listed.
- Each input is tagged with where it came from: the owner, an uploaded file, a published source, or a
  ShopFloor assumption. Unsourced assumptions are called that, and are what owner check-ins calibrate.
- Value means monthly *gross profit or owner time*, not revenue: a recovered $30 order is worth
  $30 x margin, and saved hours are valued at the owner's own hourly figure.
- If a required number is missing and no published default exists, we return `missing` instead of guessing.
"""

from dataclasses import dataclass, field

from shopfloor.catalog import assumption, industry_group
from shopfloor.models import Business, Job

WEEKS_PER_MONTH = 4.33
DEFAULT_HOURLY = 30.0


@dataclass
class JobEstimate:
    job: Job
    low: float = 0.0
    mid: float = 0.0
    high: float = 0.0
    usage: dict[str, float] = field(default_factory=dict)  # drives plan selection in pricing.py
    facts: list[str] = field(default_factory=list)  # plain-English observations for the card
    inputs: list[dict] = field(default_factory=list)  # every number used, with its origin
    missing: list[dict] = field(default_factory=list)  # {field, label} the owner must supply
    unit_value: float = 0.0  # $ of value per unit of opportunity (for break-even)
    opportunity: float = 0.0  # e.g. missed calls / month
    opportunity_label: str = ""
    time_component: float = 0.0  # reviews only: owner time a tool saves (a do-it-yourself baseline does not)

    @property
    def ok(self) -> bool:
        return not self.missing


def _src(key: str) -> dict:
    a = assumption(key)
    return {"grade": a.get("grade", "assumption"), "sources": a.get("sources", []), "note": a.get("note", "")}


def _owner(biz: Business, field_name: str, label: str, value, fmt: str = "{}") -> dict:
    origin = biz.metric_sources.get(field_name, "owner")
    return {"label": label, "value": fmt.format(value), "origin": origin, "grade": "owner", "sources": []}


def _assumed(key: str, value, fmt: str = "{}", label: str | None = None) -> dict:
    a = assumption(key)
    return {"label": label or a["label"], "value": fmt.format(value), "origin": "default", **_src(key)}


def _hourly(biz: Business, est: JobEstimate) -> float:
    m = biz.metrics
    if m.owner_hourly_value:
        est.inputs.append(_owner(biz, "owner_hourly_value", "Value of an hour of your time", m.owner_hourly_value, "${:,.0f}/h"))
        return m.owner_hourly_value
    est.inputs.append({"label": "Value of an hour of your time", "value": f"${DEFAULT_HOURLY:,.0f}/h", "origin": "default",
                       "grade": "assumption", "sources": [], "note": "Change it in your profile."})
    return DEFAULT_HOURLY


def _margin(biz: Business, est: JobEstimate) -> float:
    m = biz.metrics
    if m.gross_margin:
        est.inputs.append(_owner(biz, "gross_margin", "Gross margin on a sale", m.gross_margin, "{:.0%}"))
        return m.gross_margin
    g = assumption("gross_margin")["by_group"][industry_group(biz.industry)]
    est.inputs.append(_assumed("gross_margin", g, "{:.0%}"))
    return g


def missed_calls(biz: Business) -> JobEstimate:
    m, est = biz.metrics, JobEstimate(Job.MISSED_CALLS)
    group = industry_group(biz.industry)
    if not m.calls_per_week:
        est.missing.append({"field": "calls_per_week", "label": "Phone calls per week (or upload a call log)"})
    ticket = m.avg_ticket
    if not ticket and group == "home_services":
        ticket = assumption("avg_ticket_home_services")["mid"]
        est.inputs.append(_assumed("avg_ticket_home_services", ticket, "${:,.0f}"))
    elif ticket:
        est.inputs.append(_owner(biz, "avg_ticket", "Average order / job value", ticket, "${:,.2f}"))
    else:
        est.missing.append({"field": "avg_ticket", "label": "Average order or job value"})
    if est.missing:
        return est
    est.inputs.insert(0, _owner(biz, "calls_per_week", "Calls per week", m.calls_per_week, "{:,.0f}"))
    sh = assumption("missed_call_share")
    if m.missed_share is not None:
        shares = (m.missed_share,) * 3
        est.inputs.append(_owner(biz, "missed_share", "Calls nobody answers", m.missed_share, "{:.0%}"))
    else:
        shares = (sh["low"], sh["mid"], sh["high"])
        est.inputs.append(_assumed("missed_call_share", f"{sh['low']:.0%} / {sh['mid']:.0%} / {sh['high']:.0%}"))
    conv = assumption("callback_conversion")
    est.inputs.append(_assumed("callback_conversion", f"{conv['low']:.0%} / {conv['mid']:.0%} / {conv['high']:.0%}"))
    margin = _margin(biz, est)
    missed = [m.calls_per_week * WEEKS_PER_MONTH * s for s in shares]
    est.low, est.mid, est.high = (missed[0] * conv["low"] * ticket * margin,
                                  missed[1] * conv["mid"] * ticket * margin,
                                  missed[2] * conv["high"] * ticket * margin)
    mins = assumption("minutes_per_call")["mid"]
    est.usage = {"calls": missed[1], "unique_callers": missed[1], "conversations": missed[1], "minutes": missed[1] * mins}
    est.opportunity, est.opportunity_label = missed[1], "missed calls / month"
    est.unit_value = conv["mid"] * ticket * margin
    word = "jobs" if group == "home_services" else "orders"
    est.facts = [f"About {missed[1]:,.0f} calls a month go unanswered.",
                 f"If an AI answers them and {conv['mid']:.0%} become {word}, that is ~{missed[1] * conv['mid']:,.0f} {word} "
                 f"(${missed[1] * conv['mid'] * ticket:,.0f} in sales, ${est.mid:,.0f} after costs)."]
    return est


def review_replies(biz: Business) -> JobEstimate:
    m, est = biz.metrics, JobEstimate(Job.REVIEW_REPLIES)
    if not m.reviews_per_month:
        est.missing.append({"field": "reviews_per_month", "label": "New online reviews per month"})
        return est
    est.inputs.append(_owner(biz, "reviews_per_month", "New reviews per month", m.reviews_per_month, "{:,.0f}"))
    reply = m.reply_share if m.reply_share is not None else 0.0
    est.inputs.append(_owner(biz, "reply_share", "Reviews you reply to today", reply, "{:.0%}") if m.reply_share is not None
                      else {"label": "Reviews you reply to today", "value": "0%", "origin": "default", "grade": "assumption", "sources": []})
    hourly = _hourly(biz, est)
    mins = assumption("minutes_per_review_reply")
    est.inputs.append(_assumed("minutes_per_review_reply", mins["mid"], "{} min"))
    time_now = m.reviews_per_month * reply * mins["mid"] / 60 * hourly  # time already spent, saved by automation
    time_all = m.reviews_per_month * mins["mid"] / 60 * hourly
    rev_effect = [0.0, 0.0, 0.0]
    if m.monthly_revenue:
        est.inputs.append(_owner(biz, "monthly_revenue", "Monthly revenue", m.monthly_revenue, "${:,.0f}"))
        margin = _margin(biz, est)
        lift = assumption("rating_lift_from_replies")
        per_star = assumption("revenue_per_star")
        est.inputs.append(_assumed("rating_lift_from_replies", lift["mid"], "+{:.2f} stars"))
        est.inputs.append(_assumed("revenue_per_star", f"{per_star['mid']:.0%} - {per_star['high']:.0%}"))
        gap = 1 - reply
        food = industry_group(biz.industry) == "food"
        rev_effect = [0.0,
                      m.monthly_revenue * lift["mid"] * gap * per_star["mid"] * margin * (1.0 if food else 0.5),
                      m.monthly_revenue * lift["high"] * gap * per_star["high"] * margin]
    else:
        est.facts.append("Add monthly revenue to include the rating effect; for now this counts time only.")
    est.low, est.mid, est.high = time_now + rev_effect[0], time_all + rev_effect[1], time_all + rev_effect[2]
    unreplied = m.reviews_per_month * (1 - reply)
    est.usage = {"locations": 1}
    est.opportunity, est.opportunity_label = unreplied, "unanswered reviews / month"
    est.unit_value = est.mid / unreplied if unreplied else 0
    est.time_component = time_all
    est.facts.insert(0, f"About {unreplied:,.0f} reviews a month get no reply.")
    return est


def invoice_chasing(biz: Business) -> JobEstimate:
    m, est = biz.metrics, JobEstimate(Job.INVOICE_CHASING)
    if not m.invoices_per_month:
        est.missing.append({"field": "invoices_per_month", "label": "Invoices sent per month (or upload an invoice export)"})
    if not m.avg_invoice:
        est.missing.append({"field": "avg_invoice", "label": "Average invoice amount"})
    if est.missing:
        return est
    est.inputs.append(_owner(biz, "invoices_per_month", "Invoices per month", m.invoices_per_month, "{:,.0f}"))
    est.inputs.append(_owner(biz, "avg_invoice", "Average invoice", m.avg_invoice, "${:,.0f}"))
    if m.late_share is not None:
        late = m.late_share
        est.inputs.append(_owner(biz, "late_share", "Invoices paid late", late, "{:.0%}"))
    else:
        late = 0.3
        est.inputs.append({"label": "Invoices paid late", "value": "30%", "origin": "default", "grade": "assumption", "sources": [],
                           "note": "Tell us your real share, or upload an invoice export."})
    hourly = _hourly(biz, est)
    mins, days, rate = (assumption(k) for k in ("minutes_per_late_invoice", "days_faster_with_reminders", "cost_of_cash"))
    est.inputs += [_assumed("minutes_per_late_invoice", mins["mid"], "{} min"),
                   _assumed("days_faster_with_reminders", days["mid"], "{} days"),
                   _assumed("cost_of_cash", rate["mid"], "{:.0%} a year")]
    late_n = m.invoices_per_month * late
    late_usd = late_n * m.avg_invoice

    def val(k: str) -> float:
        return late_n * mins[k] / 60 * hourly + late_usd * days[k] / 365 * rate[k]

    est.low, est.mid, est.high = val("low"), val("mid"), val("high")
    est.usage = {"invoices": m.invoices_per_month}
    est.opportunity, est.opportunity_label = late_n, "late invoices / month"
    est.unit_value = est.mid / late_n if late_n else 0
    est.facts = [f"About {late_n:,.0f} invoices a month (${late_usd:,.0f}) go late.",
                 f"Mostly this is your time back (~{late_n * mins['mid'] / 60:,.1f} h/mo) plus getting paid ~{days['mid']} days sooner."]
    return est


def email_triage(biz: Business) -> JobEstimate:
    m, est = biz.metrics, JobEstimate(Job.EMAIL_TRIAGE)
    if not m.email_hours_per_week:
        est.missing.append({"field": "email_hours_per_week", "label": "Hours per week you spend on email"})
        return est
    users = m.email_users or 1
    est.inputs.append(_owner(biz, "email_hours_per_week", "Hours a week on email", m.email_hours_per_week, "{:,.1f} h"))
    est.inputs.append({"label": "People who need it", "value": str(users), "origin": "owner" if m.email_users else "default",
                       "grade": "owner" if m.email_users else "assumption", "sources": []})
    hourly = _hourly(biz, est)
    share = assumption("email_time_saved_share")
    est.inputs.append(_assumed("email_time_saved_share", f"{share['low']:.0%} / {share['mid']:.0%} / {share['high']:.0%}"))
    hours_month = m.email_hours_per_week * WEEKS_PER_MONTH
    est.low, est.mid, est.high = (hours_month * share[k] * hourly for k in ("low", "mid", "high"))
    est.usage = {"users": users}
    est.opportunity, est.opportunity_label = hours_month, "email hours / month"
    est.unit_value = share["mid"] * hourly
    est.facts = [f"You spend ~{hours_month:,.0f} hours a month on email.",
                 f"Saving {share['mid']:.0%} of that is ~{hours_month * share['mid']:,.0f} hours back."]
    return est


ESTIMATORS = {
    Job.MISSED_CALLS: missed_calls,
    Job.REVIEW_REPLIES: review_replies,
    Job.INVOICE_CHASING: invoice_chasing,
    Job.EMAIL_TRIAGE: email_triage,
}
