"""The core claim: predictions get sharper as verified outcomes accumulate."""

from shopfloor.models import SwipeDirection


def test_thousandth_business_gets_a_sharper_estimate(sf):
    errors = []
    for i in range(60):
        biz = sf.onboard(f"Biz {i}")
        card = next(c for c in sf.deck(biz.id) if c.tool_id == "ringback")
        hire = sf.swipe(card.id, SwipeDirection.RIGHT)
        o = sf.measure(hire.id)
        errors.append(abs(o.actual_monthly_usd - o.predicted_monthly_usd) / o.actual_monthly_usd)
    early, late = sum(errors[:10]) / 10, sum(errors[-10:]) / 10
    assert late < early, (early, late)


def test_correction_factor_converges_to_hidden_truth(sf):
    from shopfloor.models import Job, Outcome
    from shopfloor.outcomes.calibration import calibrate
    from shopfloor.outcomes.measure import SimulatedAttribution

    for i in range(60):
        biz = sf.onboard(f"Biz {i}")
        card = next(c for c in sf.deck(biz.id) if c.tool_id == "ringback")
        sf.measure(sf.swipe(card.id, SwipeDirection.RIGHT).id)
    cal = calibrate(Job.MISSED_CALLS, sf.store.list("outcomes", Outcome))
    assert abs(cal.factor - SimulatedAttribution.TRUE_RATIO[Job.MISSED_CALLS]) < 0.08
