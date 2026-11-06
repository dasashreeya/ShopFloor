"""Synthetic 90-day history for a demo business, so replay works before real OAuth exists.

Shape is tuned to a ~60-seat restaurant: lunch rush 11:30-13:30 drives most missed calls.
"""

import random
from datetime import datetime, timedelta, timezone

from shopfloor.models import ConnectorKind, Event


def generate_history(days: int = 90, seed: int = 7, end: datetime | None = None) -> list[Event]:
    rng = random.Random(seed)
    end = end or datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    events: list[Event] = []

    for d in range(days):
        day = start + timedelta(days=d)
        weekend = day.weekday() >= 5
        # orders through the POS
        for _ in range(rng.randint(70, 110) + (30 if weekend else 0)):
            ts = day + timedelta(hours=rng.uniform(11, 21))
            events.append(Event(kind="order", ts=ts, source=ConnectorKind.SQUARE,
                                attrs={"total": round(rng.lognormvariate(3.3, 0.35), 2)}))
        # inbound calls; answered unless the line is slammed
        for _ in range(rng.randint(20, 35)):
            rush = rng.random() < 0.4
            ts = day + timedelta(hours=rng.uniform(11.5, 13.5) if rush else rng.choice(
                [rng.uniform(10, 11.5), rng.uniform(13.5, 21)]))
            missed = rng.random() < (0.15 if rush else 0.04)
            events.append(Event(kind="call", ts=ts, source=ConnectorKind.PHONE,
                                attrs={"missed": missed, "rush": rush,
                                       "caller": f"+1555{rng.randint(1000000, 9999999)}"}))
        # reviews on Google Business Profile
        if rng.random() < 0.5:
            events.append(Event(kind="review", ts=day + timedelta(hours=rng.uniform(8, 23)),
                                source=ConnectorKind.GOOGLE_BUSINESS,
                                attrs={"stars": rng.choices([1, 2, 3, 4, 5], [5, 5, 10, 30, 50])[0],
                                       "replied": rng.random() < 0.2}))
        # catering / wholesale invoices in QuickBooks
        if rng.random() < 0.25:
            amount = round(rng.uniform(150, 1200), 2)
            events.append(Event(kind="invoice", ts=day, source=ConnectorKind.QUICKBOOKS,
                                attrs={"amount": amount, "days_late": max(0, int(rng.gauss(12, 15)))}))
        # inbound email
        for _ in range(rng.randint(5, 15)):
            events.append(Event(kind="email", ts=day + timedelta(hours=rng.uniform(0, 24)),
                                source=ConnectorKind.GMAIL,
                                attrs={"category": rng.choices(["catering", "vendor", "spam", "job", "complaint"], [1, 5, 6, 2, 1])[0]}))
    return sorted(events, key=lambda e: e.ts)
