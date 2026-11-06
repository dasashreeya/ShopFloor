"""Orchestrates the full loop: discover -> lab -> replay -> deck -> swipe -> measure -> recalibrate."""

import zlib
from datetime import timedelta
from functools import lru_cache

from shopfloor.connectors.synthetic import generate_history
from shopfloor.deck.cards import build_card
from shopfloor.discovery.crawler import MarketplaceSource, SeedFileSource, discover
from shopfloor.hiring import lifecycle
from shopfloor.lab.runner import run_lab
from shopfloor.llm import LLM
from shopfloor.models import (Business, Card, ConnectorKind, Crew, Event, Hire, HireStatus, LabScore, Outcome,
                              Prediction, SwipeDirection, Tool)
from shopfloor.outcomes.calibration import calibrate, published_accuracy
from shopfloor.outcomes.measure import Attribution, SimulatedAttribution, measure
from shopfloor.replay.estimators import ESTIMATORS
from shopfloor.store import Store

WINDOW_DAYS = 90
DEFAULT_ACCURACY = 0.7  # used until a tool has been through the lab


class NotFound(KeyError):
    pass


@lru_cache(maxsize=32)
def _history(seed: int) -> tuple[Event, ...]:
    return tuple(generate_history(WINDOW_DAYS, seed=seed))


class ShopFloor:
    def __init__(self, store: Store, llm: LLM, attribution: Attribution | None = None, polish_copy: bool = True):
        self.store, self.llm = store, llm
        self.attribution = attribution or SimulatedAttribution()
        self.polish_copy = polish_copy

    # ---- helpers ----
    def _get(self, coll, key, model):
        doc = self.store.get(coll, key, model)
        if doc is None:
            raise NotFound(f"{coll}/{key}")
        return doc

    def tools(self) -> list[Tool]:
        return self.store.list("tools", Tool)

    def lab_score(self, tool_id: str) -> LabScore | None:
        return self.store.get("lab", tool_id, LabScore)

    def history(self, biz: Business) -> list[Event]:
        # Demo businesses replay synthetic history; real ones would fetch from their connectors.
        return list(_history(zlib.crc32(biz.id.encode()) % 10_000))

    # ---- discovery & lab ----
    def crawl(self, sources: list[MarketplaceSource] | None = None) -> list[Tool]:
        tools = discover(sources or [SeedFileSource()], self.llm)
        for t in tools:
            self.store.put("tools", t)
        return tools

    def run_lab(self, tool_id: str) -> LabScore | None:
        score = run_lab(self._get("tools", tool_id, Tool), self.llm)
        if score:
            self.store.put("lab", score, key=tool_id)
        return score

    # ---- onboarding & replay ----
    def onboard(self, name: str, connectors: list[ConnectorKind] | None = None) -> Business:
        biz = Business(name=name, connectors=connectors or list(ConnectorKind))
        self.store.put("businesses", biz)
        return biz

    def predict(self, biz: Business, tool: Tool) -> tuple[Prediction, object] | None:
        estimator = ESTIMATORS.get(tool.job)
        if estimator is None or not set(tool.integrations) <= set(biz.connectors):
            return None
        lab = self.lab_score(tool.id)
        est = estimator(self.history(biz), WINDOW_DAYS, lab.accuracy if lab else DEFAULT_ACCURACY)
        cal = calibrate(tool.job, self.store.list("outcomes", Outcome))
        low, high = cal.widen(est.low, est.high)
        pred = Prediction(
            business_id=biz.id, tool_id=tool.id, job=tool.job, window_days=WINDOW_DAYS,
            opportunity=est.opportunity, monthly_value_usd=est.mid * cal.factor,
            monthly_value_low=low, monthly_value_high=high, monthly_cost_usd=tool.price_usd_month,
            calibration_factor=cal.factor, assumptions=est.assumptions,
        )
        return pred, est

    def _stale(self, card: Card) -> bool:
        """An undecided card is stale if its tool was lab-tested after the card was predicted."""
        lab, pred = self.lab_score(card.tool_id), self.store.get("predictions", card.prediction_id, Prediction)
        return bool(lab and pred and lab.run_at > pred.created_at)

    def deck(self, business_id: str) -> list[Card]:
        """Undecided cards, best net ROI first, one card per job (best tool for that job).

        Deals every job on first call; afterwards re-deals only undecided cards made stale by a newer lab run.
        """
        existing = self.store.list("cards", Card, business_id=business_id)
        stale = [c for c in existing if c.decision is None and self._stale(c)]
        for c in stale:
            self.store.delete("cards", c.id)
        existing = [c for c in existing if c not in stale]
        jobs = None if not existing and not stale else {c.job for c in stale}  # None = deal everything
        if jobs is None or jobs:
            biz = self._get("businesses", business_id, Business)
            best: dict = {}
            for tool in self.tools():
                if jobs is not None and tool.job not in jobs:
                    continue
                out = self.predict(biz, tool)
                if out is None:
                    continue
                pred, est = out
                if tool.job not in best or pred.net_monthly_usd > best[tool.job][0].net_monthly_usd:
                    best[tool.job] = (pred, est, tool)
            for pred, est, tool in best.values():
                self.store.put("predictions", pred)
                card = build_card(pred, tool, est, self.lab_score(tool.id), self.llm if self.polish_copy else None)
                self.store.put("cards", card)
                existing.append(card)
        open_cards = [c for c in existing if c.decision is None]
        return sorted(open_cards, key=lambda c: c.monthly_value_usd - c.monthly_cost_usd, reverse=True)

    # ---- swipe / hire / fire ----
    def swipe(self, card_id: str, direction: SwipeDirection) -> Hire | None:
        card = self._get("cards", card_id, Card)
        tool = self._get("tools", card.tool_id, Tool)
        biz = self._get("businesses", card.business_id, Business)
        hist = self.history(biz)
        recent = [e for e in hist if e.ts >= hist[-1].ts - timedelta(days=lifecycle.SHADOW_DAYS)] if hist else []
        hire = lifecycle.swipe(card, direction, tool, recent, self.llm)
        self.store.put("cards", card)
        if hire:
            self.store.put("hires", hire)
        return hire

    def promote(self, hire_id: str) -> Hire:
        hire = self._get("hires", hire_id, Hire)
        hire = lifecycle.promote(hire, self._get("tools", hire.tool_id, Tool))
        self.store.put("hires", hire)
        return hire

    def fire(self, hire_id: str) -> dict:
        hire = self._get("hires", hire_id, Hire)
        bundle = lifecycle.fire(hire)
        self.store.put("hires", hire)
        return bundle

    def hire_crew(self, business_id: str, card_ids: list[str]) -> Crew:
        hires = [self.swipe(cid, SwipeDirection.RIGHT) for cid in card_ids]
        tools = {t.id: t for t in self.tools()}
        crew = lifecycle.make_crew(business_id, [h for h in hires if h], tools)
        for h in hires:
            if h:
                self.store.put("hires", h)
        self.store.put("crews", crew)
        return crew

    def business(self, business_id: str) -> Business:
        return self._get("businesses", business_id, Business)

    def roster(self, business_id: str) -> list[dict]:
        """Every hire for a business, joined with its tool, prediction and (if measured) outcome."""
        tools = {t.id: t for t in self.tools()}
        outcomes = {o.hire_id: o for o in self.store.list("outcomes", Outcome)}
        rows = []
        for h in sorted(self.store.list("hires", Hire, business_id=business_id), key=lambda h: h.started_at):
            pred = self.store.get("predictions", h.prediction_id, Prediction)
            o = outcomes.get(h.id)
            hire = h.model_dump(mode="json", exclude={"shadow_log"})
            hire["shadow_actions"] = len(h.shadow_log)
            hire["shadow_preview"] = h.shadow_log[:5]
            rows.append({
                "hire": hire,
                "tool": tools[h.tool_id].model_dump(mode="json") if h.tool_id in tools else None,
                "prediction": pred.model_dump(mode="json") if pred else None,
                "outcome": {**o.model_dump(mode="json"), "within_interval": o.within_interval} if o else None,
            })
        return rows

    def replay_profile(self, business_id: str, tool_id: str) -> dict:
        """When, over the replay window, this tool would have acted (hour-of-day histogram)."""
        tool = self._get("tools", tool_id, Tool)
        acted = [e for e in self.history(self.business(business_id)) if lifecycle.would_have_acted(tool, e)]
        hourly = [0] * 24
        for e in acted:
            hourly[e.ts.hour] += 1
        return {"tool_id": tool_id, "window_days": WINDOW_DAYS, "actions": len(acted), "hourly": hourly,
                "peak_hour": max(range(24), key=hourly.__getitem__) if acted else None}

    # ---- outcomes ----
    def measure(self, hire_id: str) -> Outcome:
        hire = self._get("hires", hire_id, Hire)
        if hire.status != HireStatus.HIRED:
            raise lifecycle.LifecycleError("only active hires can be measured")
        pred = self._get("predictions", hire.prediction_id, Prediction)
        outcome = measure(hire, pred, self.attribution)
        self.store.put("outcomes", outcome)
        return outcome

    def accuracy(self) -> list[dict]:
        return published_accuracy(self.store.list("outcomes", Outcome))
