from datetime import datetime, timedelta, timezone

import pytest

from shopfloor.models import ConnectorKind, Event
from shopfloor.replay.estimators import missed_calls

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_missed_calls_math_is_transparent():
    events = [Event(kind="call", ts=T0 + timedelta(days=i), source=ConnectorKind.PHONE,
                    attrs={"missed": True, "rush": i % 2 == 0, "caller": f"c{i}"}) for i in range(90)]
    events += [Event(kind="order", ts=T0, source=ConnectorKind.SQUARE, attrs={"total": 40.0})]
    est = missed_calls(events, window_days=90, accuracy=1.0)
    # 90 unique callers / 90 days -> 30 per month x 25% recover x $40 ticket
    assert est.mid == pytest.approx(300.0)
    assert est.low < est.mid < est.high
    assert est.facts["missed"] == 90 and est.facts["rush"] == 45


def test_no_events_means_no_value():
    est = missed_calls([], window_days=90, accuracy=0.9)
    assert est.mid == 0 and est.facts["missed"] == 0
