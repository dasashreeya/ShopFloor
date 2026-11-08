import pytest

from shopfloor.llm import FakeLLM
from shopfloor.service import ShopFloor
from shopfloor.store import Store

PIZZA = dict(name="Test Pizza", industry="restaurant", stack=["square", "google_business", "gmail", "quickbooks"],
             budget_usd_month=150, pains=["missed_calls", "review_replies"],
             metrics=dict(calls_per_week=180, missed_share=0.25, avg_ticket=32, reviews_per_month=25, reply_share=0.1,
                          monthly_revenue=60000, invoices_per_month=6, avg_invoice=450, email_hours_per_week=4))
HVAC = dict(name="Test HVAC", industry="hvac", stack=["jobber", "quickbooks", "google_business", "google_workspace", "gmail"],
            budget_usd_month=300, needs={"human_handoff": True},
            metrics=dict(calls_per_week=60, reviews_per_month=8, invoices_per_month=70, avg_invoice=620, late_share=0.35,
                         email_hours_per_week=6, uses_builtin_reminders=False))


@pytest.fixture
def sf() -> ShopFloor:
    return ShopFloor(Store(":memory:"), FakeLLM())
