"""30 days after a hire, measure what the tool actually delivered.

`Attribution` is the seam: the real one joins tool action logs to POS/accounting records
(e.g. texted caller's phone number -> a Square order within 48h). `SimulatedAttribution`
lets the demo exercise the calibration loop with a hidden "true" effect per job.
"""

import random
from typing import Protocol

from shopfloor.models import Hire, Job, Outcome, Prediction

MEASURE_DAYS = 30


class Attribution(Protocol):
    def actual_monthly_usd(self, hire: Hire, prediction: Prediction) -> float: ...


class SimulatedAttribution:
    # Hidden truth the platform does not know: our priors are optimistic for missed calls, etc.
    TRUE_RATIO = {Job.MISSED_CALLS: 0.7, Job.REVIEW_REPLIES: 1.2, Job.INVOICE_CHASING: 0.9, Job.EMAIL_TRIAGE: 0.6}

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def actual_monthly_usd(self, hire: Hire, prediction: Prediction) -> float:
        raw = prediction.monthly_value_usd / prediction.calibration_factor  # undo our correction
        return raw * self.TRUE_RATIO.get(prediction.job, 1.0) * self.rng.lognormvariate(0, 0.3)


def measure(hire: Hire, prediction: Prediction, attribution: Attribution) -> Outcome:
    return Outcome(
        hire_id=hire.id, prediction_id=prediction.id, job=prediction.job, days_measured=MEASURE_DAYS,
        predicted_monthly_usd=prediction.monthly_value_usd,
        raw_predicted_monthly_usd=prediction.monthly_value_usd / prediction.calibration_factor,
        predicted_low=prediction.monthly_value_low,
        predicted_high=prediction.monthly_value_high,
        actual_monthly_usd=round(attribution.actual_monthly_usd(hire, prediction), 2),
    )
