import pytest

from shopfloor.hiring.lifecycle import LifecycleError
from shopfloor.models import HireStatus, SwipeDirection


def _card(sf, tool_id="ringback"):
    biz = sf.onboard("Luna Taqueria")
    return next(c for c in sf.deck(biz.id) if c.tool_id == tool_id), biz


def test_left_is_pass_and_cannot_double_swipe(sf):
    card, biz = _card(sf)
    assert sf.swipe(card.id, SwipeDirection.LEFT) is None
    assert card.id not in {c.id for c in sf.deck(biz.id)}
    with pytest.raises(LifecycleError):
        sf.swipe(card.id, SwipeDirection.RIGHT)


def test_shadow_is_read_only_and_logs_would_have_actions(sf):
    card, _ = _card(sf)
    hire = sf.swipe(card.id, SwipeDirection.UP)
    assert hire.status == HireStatus.SHADOW
    assert hire.granted_scopes and all("read" in s.lower() for s in hire.granted_scopes)
    assert "phone:sms:send" not in hire.granted_scopes
    assert hire.shadow_log and "draft" in hire.shadow_log[0]
    assert not hire.billing


def test_promote_then_fire_revokes_exports_cancels(sf):
    card, _ = _card(sf)
    hire = sf.promote(sf.swipe(card.id, SwipeDirection.UP).id)
    assert hire.status == HireStatus.HIRED and "phone:sms:send" in hire.granted_scopes
    bundle = sf.fire(hire.id)
    assert "phone:sms:send" in bundle["revoked_scopes"]
    assert bundle["billing"]["status"] == "cancelled"
    assert bundle["export"]["status"] == "fired" and bundle["export"]["granted_scopes"] == []
    with pytest.raises(LifecycleError):
        sf.fire(hire.id)


def test_crew_routes_events_to_the_right_tools(sf):
    biz = sf.onboard("Luna Taqueria")
    cards = sf.deck(biz.id)
    crew = sf.hire_crew(biz.id, [c.id for c in cards])
    assert set(crew.routes) == {"call", "review", "invoice", "email"}
    assert len(crew.hire_ids) == len(cards)


def test_lab_run_refreshes_undecided_cards_only(sf):
    biz = sf.onboard("Luna Taqueria")
    before = {c.job: c for c in sf.deck(biz.id)}
    passed = before["review_replies"]
    sf.swipe(passed.id, SwipeDirection.LEFT)
    assert before["missed_calls"].lab_accuracy is None

    sf.run_lab("ringback")
    sf.run_lab("replybird")
    after = {c.job: c for c in sf.deck(biz.id)}
    assert after["missed_calls"].lab_accuracy == sf.lab_score(after["missed_calls"].tool_id).accuracy
    assert after["missed_calls"].id != before["missed_calls"].id
    assert "review_replies" not in after  # a decided job is never re-dealt
    assert after["invoice_chasing"].id == before["invoice_chasing"].id  # untouched jobs keep their card
    assert len(sf.deck(biz.id)) == len(after)  # idempotent: no re-deal without a newer lab run
