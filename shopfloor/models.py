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
    """A job-to-be-done. Recommendations are made one job at a time."""

    MISSED_CALLS = "missed_calls"
    REVIEW_REPLIES = "review_replies"
    INVOICE_CHASING = "invoice_chasing"
    EMAIL_TRIAGE = "email_triage"


# Software a small business may already use. Free-form strings so the catalog can grow without code changes.
KNOWN_SOFTWARE = {
    "square": "Square", "toast": "Toast", "clover": "Clover",
    "quickbooks": "QuickBooks Online", "xero": "Xero", "freshbooks": "FreshBooks",
    "jobber": "Jobber", "housecall_pro": "Housecall Pro", "servicetitan": "ServiceTitan",
    "gmail": "Gmail", "google_workspace": "Google Workspace", "outlook": "Outlook / Microsoft 365",
    "google_business": "Google Business Profile", "yelp": "Yelp",
    "opentable": "OpenTable", "resy": "Resy", "calendly": "Calendly", "stripe": "Stripe",
}


# ---------- catalog ----------


class Plan(BaseModel):
    name: str
    usd_month: float
    included: float | None = None  # units included per month (None = unlimited / flat)
    overage: float | None = None  # USD per unit beyond included (None = not published)
    notes: str = ""


class Pricing(BaseModel):
    url: str
    evidence: str  # vendor_page | vendor_help_center | secondary_source | llm_extracted
    unit: str = "flat"
    plans: list[Plan] = Field(default_factory=list)
    quote_only: bool = False
    trial: str = ""
    contract: str = ""
    notes: str = ""


class Rating(BaseModel):
    platform: str
    score: float | None
    count: int
    url: str
    note: str = ""
    relevance: str = "high"  # "low" when most of the platform's reviews are about a different product


class Review(BaseModel):
    platform: str
    url: str
    author: str
    date: str | None = None
    stars: int | None = None
    quote: str
    theme: str = ""
    relevant: bool = True
    relevance_note: str = ""


class Tool(BaseModel):
    """A real product (or a free built-in feature of software the owner already has)."""

    id: str
    name: str
    vendor: str
    kind: str = "product"  # product | addon | builtin | candidate (auto-discovered, unverified)
    jobs: list[Job]
    verticals: list[str] = Field(default_factory=lambda: ["all"])
    summary: str = ""
    website: str = ""
    pricing: Pricing
    requires_any: list[str] = Field(default_factory=list)  # needs at least one of these in the stack
    works_with: list[str] = Field(default_factory=list)
    capabilities: dict[str, bool | None] = Field(default_factory=dict)
    capability_notes: dict[str, str] = Field(default_factory=dict)
    ratings: list[Rating] = Field(default_factory=list)
    reviews: list[Review] = Field(default_factory=list)
    evidence_gap: str = ""
    engage: dict[str, str] = Field(default_factory=dict)
    behavior: str = ""  # documented behavior, used by the scenario lab simulator
    baseline_saves_time: bool = True
    retrieved: str = ""


class LabScore(BaseModel):
    tool_id: str
    job: Job
    accuracy: float
    p50_latency_s: float
    cost_per_resolved_usd: float | None  # None when nothing passed
    n_tasks: int
    model: str
    simulated: bool = True
    run_at: datetime = Field(default_factory=now)
    failures: list[dict] = Field(default_factory=list)


# ---------- owner intake ----------


class Metrics(BaseModel):
    """The owner's own numbers (typed in, or computed from an uploaded CSV). None = unknown."""

    monthly_revenue: float | None = None
    avg_ticket: float | None = None
    gross_margin: float | None = None
    calls_per_week: float | None = None
    missed_share: float | None = None
    reviews_per_month: float | None = None
    reply_share: float | None = None
    invoices_per_month: float | None = None
    late_share: float | None = None
    avg_invoice: float | None = None
    email_hours_per_week: float | None = None
    email_users: int | None = None
    owner_hourly_value: float | None = None
    uses_builtin_reminders: bool | None = None


class Business(BaseModel):
    id: str = Field(default_factory=lambda: new_id("biz"))
    name: str
    industry: str = "other"
    zip: str = ""
    stack: list[str] = Field(default_factory=list)
    budget_usd_month: float | None = None
    needs: dict[str, bool] = Field(default_factory=dict)  # spanish, human_handoff, no_contract
    pains: list[Job] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    metric_sources: dict[str, str] = Field(default_factory=dict)  # field -> "owner" | "csv:<file>"
    revision: int = 1
    created_at: datetime = Field(default_factory=now)


# ---------- recommendations ----------


class Adoption(StrEnum):
    TRIAL = "trial"
    ADOPTED = "adopted"
    CANCELLED = "cancelled"
    PASSED = "passed"


class Pick(BaseModel):
    """One business's decision on one tool, plus the estimate shown when they made it."""

    id: str = Field(default_factory=lambda: new_id("pick"))
    business_id: str
    tool_id: str
    job: Job
    status: Adoption
    estimate: dict[str, Any] = Field(default_factory=dict)  # snapshot of value/cost/assumptions at decision time
    started_at: datetime = Field(default_factory=now)
    adopted_at: datetime | None = None
    cancelled_at: datetime | None = None
    checklist: list[dict] = Field(default_factory=list)


class Outcome(BaseModel):
    """Owner-reported result at a check-in. This is the only source of 'actual' numbers."""

    id: str = Field(default_factory=lambda: new_id("out"))
    pick_id: str
    business_id: str
    tool_id: str
    job: Job
    days_since_start: int
    predicted_monthly_usd: float
    raw_predicted_monthly_usd: float
    predicted_low: float
    predicted_high: float
    actual_monthly_usd: float
    reported_inputs: dict[str, float] = Field(default_factory=dict)
    note: str = ""
    measured_at: datetime = Field(default_factory=now)

    @property
    def ratio(self) -> float:
        return self.actual_monthly_usd / self.raw_predicted_monthly_usd if self.raw_predicted_monthly_usd else 0.0

    @property
    def within_interval(self) -> bool:
        return self.predicted_low <= self.actual_monthly_usd <= self.predicted_high
