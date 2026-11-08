"""Owner check-ins: what actually happened after a tool was turned on.

The owner reports a few plain numbers (from the tool's own dashboard or their POS); we convert them to monthly
value with the *same* margin and hourly figures used for the prediction, so prediction and outcome are comparable.
This is self-reported evidence and is labeled that way everywhere it appears.
"""

from shopfloor.engine.estimators import DEFAULT_HOURLY, WEEKS_PER_MONTH
from shopfloor.models import Business, Job

# What we ask at check-in, per job. key -> (question, unit)
QUESTIONS: dict[Job, list[tuple[str, str, str]]] = {
    Job.MISSED_CALLS: [("won_from_ai_calls", "Orders or jobs that came from calls the AI handled (last 30 days)", "count"),
                       ("hours_saved_month", "Hours of your time it saved (last 30 days)", "hours")],
    Job.REVIEW_REPLIES: [("hours_saved_month", "Hours of your time it saved (last 30 days)", "hours"),
                         ("extra_value_usd", "Any other value you'd put on it this month ($)", "usd")],
    Job.INVOICE_CHASING: [("hours_saved_month", "Hours of chasing it saved (last 30 days)", "hours"),
                          ("collected_after_reminder_usd", "Late money collected after its reminders ($)", "usd")],
    Job.EMAIL_TRIAGE: [("hours_saved_week", "Hours a week it saves you", "hours")],
}


def actual_value(job: Job, biz: Business, inputs: dict[str, float], assumed_margin: float) -> float:
    m = biz.metrics
    hourly = m.owner_hourly_value or DEFAULT_HOURLY
    hours = inputs.get("hours_saved_month", 0.0) + inputs.get("hours_saved_week", 0.0) * WEEKS_PER_MONTH
    value = hours * hourly + inputs.get("extra_value_usd", 0.0)
    if job == Job.MISSED_CALLS:
        value += inputs.get("won_from_ai_calls", 0.0) * (m.avg_ticket or 0.0) * assumed_margin
    if job == Job.INVOICE_CHASING:
        # money collected sooner is worth its financing cost, not its face value (same assumption as the estimate)
        value += inputs.get("collected_after_reminder_usd", 0.0) * 4 / 365 * 0.15
    return round(value, 2)
