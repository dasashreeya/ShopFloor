"""The moat: verified outcomes recalibrate predictions, and we publish our own accuracy.

Per job, we model log(actual / predicted) ~ Normal(mu, SIGMA^2) with prior mu ~ Normal(0, TAU^2).
The posterior mean of mu gives a multiplicative correction; its sd tightens with every
verified hire, so the 1000th business gets a sharper interval than the first.
"""

import math
from dataclasses import dataclass

from shopfloor.models import Job, Outcome

TAU = 0.5  # prior sd of systematic bias (log scale): "our priors are within ~1.6x"
SIGMA = 0.4  # per-business noise around the systematic bias


@dataclass
class Calibration:
    job: Job
    n: int
    factor: float  # multiply raw predictions by this
    log_sd: float  # remaining uncertainty about the bias (log scale)

    def widen(self, low: float, high: float) -> tuple[float, float]:
        """Apply factor and add bias uncertainty to a raw [low, high] interval (90%)."""
        spread = math.exp(1.645 * self.log_sd)
        return low * self.factor / spread, high * self.factor * spread


def calibrate(job: Job, outcomes: list[Outcome]) -> Calibration:
    logs = [math.log(o.ratio) for o in outcomes if o.job == job and o.ratio > 0]
    n = len(logs)
    precision = 1 / TAU**2 + n / SIGMA**2
    mu = (sum(logs) / SIGMA**2) / precision
    return Calibration(job=job, n=n, factor=math.exp(mu), log_sd=math.sqrt(1 / precision))


def published_accuracy(outcomes: list[Outcome]) -> list[dict]:
    """What we publish: per job, how wrong were we, and are we getting less wrong."""
    report = []
    for job in sorted({o.job for o in outcomes}):
        rows = sorted((o for o in outcomes if o.job == job), key=lambda o: o.measured_at)
        ape = [abs(o.actual_monthly_usd - o.predicted_monthly_usd) / o.actual_monthly_usd
               for o in rows if o.actual_monthly_usd > 0]
        half = len(ape) // 2
        cal = calibrate(job, rows)
        report.append({
            "job": job.value,
            "reported_outcomes": len(rows),
            "mape": round(sum(ape) / len(ape), 3) if ape else None,
            "mape_first_half": round(sum(ape[:half]) / half, 3) if half else None,
            "mape_second_half": round(sum(ape[half:]) / (len(ape) - half), 3) if len(ape) - half and half else None,
            "interval_coverage": round(sum(o.within_interval for o in rows) / len(rows), 3),
            "current_correction_factor": round(cal.factor, 3),
        })
    return report
