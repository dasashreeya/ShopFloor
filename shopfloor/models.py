"""Domain models. Everything persisted is a pydantic model stored as JSON in the doc store."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class Job(StrEnum):
    """A job-to-be-done. Cards are dealt one job at a time."""

    MISSED_CALLS = "missed_calls"
    REVIEW_REPLIES = "review_replies"
    INVOICE_CHASING = "invoice_chasing"
    EMAIL_TRIAGE = "email_triage"
    OTHER = "other"


class ConnectorKind(StrEnum):
    SQUARE = "square"
    TOAST = "toast"
    QUICKBOOKS = "quickbooks"
    GMAIL = "gmail"
    PHONE = "phone"
    GOOGLE_BUSINESS = "google_business"


class Event(BaseModel):
    """Normalized event emitted by any connector (call, order, email, review, invoice)."""

    kind: str
    ts: datetime
    source: ConnectorKind
    attrs: dict[str, Any] = Field(default_factory=dict)


class Business(BaseModel):
    id: str = Field(default_factory=lambda: new_id("biz"))
    name: str
    vertical: str = "restaurant"
    connectors: list[ConnectorKind] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now)


# ---------- catalog & lab ----------


class Tool(BaseModel):
    """An AI tool discovered by crawling marketplaces (vendors never self-submit)."""

    id: str
    name: str
    vendor: str
    job: Job
    price_usd_month: float
    source: str  # marketplace it was discovered on
    listing_url: str = ""
    integrations: list[ConnectorKind] = Field(default_factory=list)
    summary: str = ""
    behavior: str = ""  # how the tool behaves; drives the lab simulator until a real adapter exists
    discovered_at: datetime = Field(default_factory=now)


class LabScore(BaseModel):
    tool_id: str
    job: Job
    accuracy: float  # share of golden tasks passed
    p50_latency_s: float
    cost_per_resolved_usd: float  # inference cost / tasks passed
    n_tasks: int
    model: str
    run_at: datetime = Field(default_factory=now)
    failures: list[dict] = Field(default_factory=list)


# ---------- prediction & deck ----------


class Prediction(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pred"))
    business_id: str
    tool_id: str
    job: Job
    window_days: int = 90
    opportunity: dict[str, float]  # e.g. {"missed_calls": 142}
    monthly_value_usd: float  # point estimate after calibration
    monthly_value_low: float
    monthly_value_high: float
    monthly_cost_usd: float
    calibration_factor: float = 1.0
    assumptions: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=now)

    @property
    def net_monthly_usd(self) -> float:
        return self.monthly_value_usd - self.monthly_cost_usd


class SwipeDirection(StrEnum):
    LEFT = "left"  # pass
    UP = "up"  # 14-day shadow shift
    RIGHT = "right"  # hire


class Card(BaseModel):
    id: str = Field(default_factory=lambda: new_id("card"))
    business_id: str
    prediction_id: str
    tool_id: str
    tool_name: str
    job: Job
    headline: str
    body: str
    monthly_value_usd: float
    monthly_value_low: float
    monthly_value_high: float
    monthly_cost_usd: float
    lab_accuracy: float | None = None
    stats: list[dict] = Field(default_factory=list)  # replay findings tiles: {label, value, accent}
    decision: SwipeDirection | None = None


# ---------- hiring lifecycle ----------


class HireStatus(StrEnum):
    SHADOW = "shadow"
    HIRED = "hired"
    FIRED = "fired"


class Hire(BaseModel):
    id: str = Field(default_factory=lambda: new_id("hire"))
    business_id: str
    tool_id: str
    prediction_id: str
    crew_id: str | None = None
    status: HireStatus
    granted_scopes: list[str] = Field(default_factory=list)
    shadow_log: list[dict] = Field(default_factory=list)  # actions the tool *would* have taken
    billing: dict = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=now)
    shadow_ends_at: datetime | None = None
    hired_at: datetime | None = None
    fired_at: datetime | None = None


class Crew(BaseModel):
    """Several tools hired together; the platform owns the wiring between them."""

    id: str = Field(default_factory=lambda: new_id("crew"))
    business_id: str
    hire_ids: list[str]
    routes: dict[str, list[str]]  # event kind -> hire ids that receive it


# ---------- outcomes ----------


class Outcome(BaseModel):
    id: str = Field(default_factory=lambda: new_id("out"))
    hire_id: str
    prediction_id: str
    job: Job
    days_measured: int
    predicted_monthly_usd: float  # what we showed the owner (calibrated)
    raw_predicted_monthly_usd: float  # our model before calibration; calibration learns on this
    predicted_low: float
    predicted_high: float
    actual_monthly_usd: float
    measured_at: datetime = Field(default_factory=now)

    @property
    def ratio(self) -> float:
        """actual / raw model output. Using the calibrated number here would make the loop
        learn only residual bias and drift back toward 1."""
        return self.actual_monthly_usd / self.raw_predicted_monthly_usd if self.raw_predicted_monthly_usd else 0.0

    @property
    def within_interval(self) -> bool:
        return self.predicted_low <= self.actual_monthly_usd <= self.predicted_high
