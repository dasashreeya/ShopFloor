from shopfloor.deck.cards import _polish
from shopfloor.llm.base import LLMResult


class Stub:
    def __init__(self, headline):
        self.data = {"headline": headline}

    def chat(self, *a, **k):
        return LLMResult(text="", model="stub", latency_s=0, data=self.data)


def test_llm_headline_cannot_invent_numbers():
    h = "You missed 142 calls, 90 over the lunch rush."
    assert _polish(Stub("You missed 500 calls!"), h) == h


def test_llm_headline_kept_when_numbers_match():
    h = "You missed 142 calls, 90 over the lunch rush."
    assert _polish(Stub("142 calls went unanswered, 90 at lunch"), h) == "142 calls went unanswered, 90 at lunch"


def test_body_money_sentence_is_never_rewritten(sf):
    biz = sf.onboard("Luna Taqueria")
    for card in sf.deck(biz.id):
        assert card.body.endswith(f"against ${card.monthly_cost_usd:,.0f}/month.")
