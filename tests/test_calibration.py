import random

from shopfloor.models import Job, Outcome
from shopfloor.outcomes.calibration import calibrate, published_accuracy


def outcomes(n, ratio, seed=1):
    rng = random.Random(seed)
    return [Outcome(pick_id=f"h{i}", business_id="b", tool_id="t", job=Job.MISSED_CALLS, days_since_start=30,
                    predicted_monthly_usd=100, raw_predicted_monthly_usd=100, predicted_low=60, predicted_high=140,
                    actual_monthly_usd=100 * ratio * rng.lognormvariate(0, 0.3)) for i in range(n)]


def test_no_data_is_neutral():
    c = calibrate(Job.MISSED_CALLS, [])
    assert c.factor == 1.0 and c.n == 0


def test_converges_and_tightens_with_evidence():
    few, many = calibrate(Job.MISSED_CALLS, outcomes(3, 0.6)), calibrate(Job.MISSED_CALLS, outcomes(200, 0.6))
    assert abs(many.factor - 0.6) < abs(few.factor - 0.6)
    assert abs(many.factor - 0.6) < 0.05
    assert many.log_sd < few.log_sd


def test_published_accuracy_shape():
    [row] = published_accuracy(outcomes(10, 0.8))
    assert row["job"] == "missed_calls" and row["reported_outcomes"] == 10
    assert 0 <= row["interval_coverage"] <= 1
