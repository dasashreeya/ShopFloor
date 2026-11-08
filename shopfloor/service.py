"""Orchestrates: intake -> recommend -> try / adopt -> check in -> recalibrate -> publish accuracy."""

import json
import math
from pathlib import Path

from shopfloor.catalog import assumption, catalog_tools, industry_group, research
from shopfloor.config import get_settings
from shopfloor.discovery import extract, page_text
from shopfloor.engine.estimators import ESTIMATORS
from shopfloor.engine.intake import PARSERS
from shopfloor.engine.recommend import JOB_LABELS, recommend
from shopfloor.lab.runner import run_lab
from shopfloor.llm import LLM
from shopfloor.models import Adoption, Business, Job, LabScore, Metrics, Outcome, Pick, Tool, now
from shopfloor.outcomes.calibration import calibrate, published_accuracy
from shopfloor.outcomes.checkin import QUESTIONS, actual_value
from shopfloor.store import Store

LAB_SNAPSHOT = Path(__file__).parent / "lab" / "results.json"  # lab runs committed with the repo (simulated)
MIN_DAYS_FOR_CALIBRATION = 14


class NotFound(KeyError):
    pass


class Invalid(ValueError):
    pass


ADOPTION_STEPS = {
    Job.MISSED_CALLS: ["Start the trial and give the agent your hours, services/menu and FAQs",
                       "Forward unanswered calls (after 3-4 rings) from your phone line to the AI number",
                       "Set the hand-off rule: who gets urgent calls, and by text or transfer",
                       "Call it yourself 5 times with real customer questions before going live",
                       "Mark your calendar: check in here after 30 days"],
    Job.REVIEW_REPLIES: ["Connect your Google Business Profile (you must be a verified owner/manager)",
                         "Turn on approve-before-posting for the first two weeks",
                         "Write 2-3 rules: never offer refunds publicly, always invite unhappy customers to call",
                         "Check in here after 30 days"],
    Job.INVOICE_CHASING: ["Connect QuickBooks or Xero (read invoices, send reminders)",
                          "Pick a schedule: 3 days before due, on the due date, 7 and 14 days after",
                          "Exclude your best long-term customers if you prefer to call them",
                          "Check in here after 30 days"],
    Job.EMAIL_TRIAGE: ["Connect your Gmail/Outlook account", "Let it sort for a week before trusting its folders",
                       "Review drafts before sending for the first two weeks", "Check in here after 30 days"],
}
EXIT_STEPS = ["Cancel in the vendor's billing page (note the vendor's own terms below)",
              "Revoke its access: Google Account > Security > Third-party access, or QuickBooks/Xero > Connected apps",
              "Turn off call forwarding to the AI number if you set it up",
              "Export any call logs/messages you want to keep"]


class ShopFloor:
    def __init__(self, store: Store, llm: LLM):
        self.store, self.llm = store, llm
        self._tools = {t.id: t for t in catalog_tools()}
        if LAB_SNAPSHOT.exists():
            for s in json.loads(LAB_SNAPSHOT.read_text(encoding="utf-8")):
                if not self.store.get("lab", s["tool_id"], LabScore):
                    self.store.put("lab", LabScore(**s), key=s["tool_id"])

    # ---- catalog ----
    def tools(self, include_candidates: bool = True) -> list[Tool]:
        tools = list(self._tools.values())
        if include_candidates:
            tools += self.store.list("candidates", Tool)
        return tools

    def tool(self, tool_id: str) -> Tool:
        t = self._tools.get(tool_id) or self.store.get("candidates", tool_id, Tool)
        if t is None:
            raise NotFound(f"tool/{tool_id}")
        return t

    def lab_scores(self) -> dict[str, dict]:
        return {s.tool_id: s.model_dump(mode="json") for s in self.store.list("lab", LabScore)}

    def run_lab(self, tool_id: str) -> LabScore | None:
        tool = self.tool(tool_id)
        if not tool.behavior:
            raise Invalid("This is a built-in feature; there is nothing to simulate")
        score = run_lab(tool, self.llm)
        if score:
            self.store.put("lab", score, key=tool_id)
        return score

    def discover(self, url: str) -> Tool:
        cand = extract(url, page_text(url), self.llm)
        self.store.put("candidates", cand)
        return cand

    def try_tool(self, tool_id: str, text: str) -> dict:
        tool = self.tool(tool_id)
        if not tool.behavior:
            raise Invalid("Built-in features can't be simulated")
        text = text.strip()[:1500]
        if not text:
            raise Invalid("Paste a real review, email or call note to try")
        res = self.llm.chat(
            [{"role": "system", "content": f"[task:try-tool] {tool.behavior} Respond with only the reply you would send."},
             {"role": "user", "content": text}],
            model=get_settings().model_fast, max_tokens=300)
        return {"tool_id": tool_id, "reply": res.text, "model": res.model, "simulated": True,
                "note": f"Simulated from {tool.vendor}'s documented behavior on {res.model}. Not output from {tool.name} itself."}

    # ---- businesses ----
    def _get(self, coll, key, model):
        doc = self.store.get(coll, key, model)
        if doc is None:
            raise NotFound(f"{coll}/{key}")
        return doc

    def business(self, business_id: str) -> Business:
        return self._get("businesses", business_id, Business)

    @staticmethod
    def _clean(data: dict) -> dict:
        if "pains" in data:
            data["pains"] = [p for p in data["pains"] if p in Job._value2member_map_]
        if "stack" in data:
            data["stack"] = sorted({s.strip().lower() for s in data["stack"] if s and len(s) < 40})
        return data

    def onboard(self, data: dict) -> Business:
        biz = Business(**self._clean(data))
        if not biz.name.strip():
            raise Invalid("Business name is required")
        biz.metric_sources = {k: "owner" for k, v in biz.metrics.model_dump().items() if v is not None}
        self.store.put("businesses", biz)
        return biz

    def update(self, business_id: str, data: dict) -> Business:
        biz, data = self.business(business_id), self._clean(data)
        metrics = {**biz.metrics.model_dump(), **(data.pop("metrics", None) or {})}
        sources = dict(biz.metric_sources)
        for k, v in metrics.items():
            if v is not None and getattr(biz.metrics, k) != v:
                sources[k] = "owner"
        new = biz.model_copy(update={**data, "metrics": Metrics(**metrics), "metric_sources": sources, "revision": biz.revision + 1})
        Business.model_validate(new.model_dump())
        self.store.put("businesses", new)
        return new

    def import_csv(self, business_id: str, kind: str, text: str, filename: str = "upload.csv") -> dict:
        if kind not in PARSERS:
            raise Invalid(f"kind must be one of {', '.join(PARSERS)}")
        result = PARSERS[kind](text)
        biz = self.business(business_id)
        metrics = {**biz.metrics.model_dump(), **result["metrics"]}
        sources = {**biz.metric_sources, **{k: f"file: {filename}" for k in result["metrics"]}}
        biz = biz.model_copy(update={"metrics": Metrics(**metrics), "metric_sources": sources, "revision": biz.revision + 1})
        self.store.put("businesses", biz)
        return {**result, "business": biz.model_dump(mode="json")}

    # ---- recommendations ----
    def _calibrated(self, rec: dict) -> dict:
        """Apply per-job calibration learned from owner check-ins (no-op until there are enough)."""
        outs = self._calibration_outcomes()
        for job in rec["jobs"]:
            cal = calibrate(Job(job["job"]), outs)
            job["calibration"] = {"n": cal.n, "factor": round(cal.factor, 3)}
            if cal.n:
                for o in job.get("options", []):
                    for k in ("monthly_value_low", "monthly_value", "monthly_value_high"):
                        o[k] = round(o[k] * cal.factor)
                    if o["monthly_cost"] is not None:
                        o["net_monthly"] = round(o["monthly_value"] - o["monthly_cost"])
        return rec

    def recommendations(self, business_id: str) -> dict:
        biz = self.business(business_id)
        rec = self._calibrated(recommend(biz, self.tools(include_candidates=False), self.lab_scores()))
        picks = {p.tool_id: p.status for p in self.store.list("picks", Pick, business_id=business_id)}
        for job in rec["jobs"]:
            for o in job.get("options", []):
                o["decision"] = picks.get(o["tool_id"])
        rec["business"] = biz.model_dump(mode="json")
        return rec

    def tool_for_business(self, business_id: str, tool_id: str) -> dict:
        """One tool scored for this business: the dossier's 'fit for you' panel and the compare table."""
        biz, tool = self.business(business_id), self.tool(tool_id)
        if tool.kind == "candidate" or not tool.jobs:
            return {"tool_id": tool_id, "eligible": False, "reasons": ["Unverified candidate: not scored yet"]}
        rec = recommend(biz, self.tools(include_candidates=False), self.lab_scores())
        job = next(j for j in rec["jobs"] if j["job"] == tool.jobs[0].value)
        opt = next((o for o in job.get("options", []) if o["tool_id"] == tool_id), None)
        dq = next((d for d in job.get("disqualified", []) if d["tool_id"] == tool_id), None)
        return {"tool_id": tool_id, "job": job["job"], "status": job["status"], "missing": job["missing"],
                "eligible": opt is not None, "option": opt, "reasons": dq["reasons"] if dq else [],
                "inputs": job["inputs"], "facts": job["facts"]}

    # ---- adoption ----
    def decide(self, business_id: str, tool_id: str, action: str) -> Pick:
        biz, tool = self.business(business_id), self.tool(tool_id)
        if tool.kind == "candidate":
            raise Invalid("Unverified candidates can't be adopted yet")
        if action not in ("trial", "adopt", "pass"):
            raise Invalid("action must be trial, adopt or pass")
        existing = [p for p in self.store.list("picks", Pick, business_id=business_id, tool_id=tool_id)
                    if p.status in (Adoption.TRIAL, Adoption.ADOPTED)]
        if existing and action != "adopt":
            raise Invalid(f"{tool.name} is already {existing[0].status.value}")
        if existing and action == "adopt":
            return self.adopt(existing[0].id, business_id)
        snap = self.tool_for_business(business_id, tool_id).get("option") or {}
        job = tool.jobs[0]
        status = {"trial": Adoption.TRIAL, "adopt": Adoption.ADOPTED, "pass": Adoption.PASSED}[action]
        pick = Pick(business_id=biz.id, tool_id=tool.id, job=job, status=status,
                    estimate={k: snap.get(k) for k in ("monthly_value_low", "monthly_value", "monthly_value_high", "monthly_cost", "plan", "score")}
                    | {"margin": self._margin(biz), "revision": biz.revision},
                    adopted_at=now() if status == Adoption.ADOPTED else None,
                    checklist=[{"step": s, "done": False} for s in ADOPTION_STEPS[job]] if status != Adoption.PASSED else [])
        self.store.put("picks", pick)
        return pick

    def _margin(self, biz: Business) -> float:
        return biz.metrics.gross_margin or assumption("gross_margin")["by_group"][industry_group(biz.industry)]

    def _pick(self, pick_id: str, business_id: str) -> Pick:
        pick = self._get("picks", pick_id, Pick)
        if pick.business_id != business_id:
            raise NotFound(f"picks/{pick_id}")
        return pick

    def adopt(self, pick_id: str, business_id: str) -> Pick:
        pick = self._pick(pick_id, business_id)
        if pick.status != Adoption.TRIAL:
            raise Invalid(f"Only a trial can be adopted (this one is {pick.status.value})")
        pick.status, pick.adopted_at = Adoption.ADOPTED, now()
        self.store.put("picks", pick)
        return pick

    def toggle_step(self, pick_id: str, business_id: str, index: int) -> Pick:
        pick = self._pick(pick_id, business_id)
        if not 0 <= index < len(pick.checklist):
            raise Invalid("No such step")
        pick.checklist[index]["done"] = not pick.checklist[index]["done"]
        self.store.put("picks", pick)
        return pick

    def cancel(self, pick_id: str, business_id: str) -> dict:
        pick = self._pick(pick_id, business_id)
        if pick.status not in (Adoption.TRIAL, Adoption.ADOPTED):
            raise Invalid(f"Nothing to cancel (status {pick.status.value})")
        pick.status, pick.cancelled_at = Adoption.CANCELLED, now()
        self.store.put("picks", pick)
        tool = self.tool(pick.tool_id)
        return {"pick": pick.model_dump(mode="json"), "exit_steps": EXIT_STEPS, "vendor_terms": tool.pricing.contract or "Not stated",
                "cancel_url": tool.engage.get("signup_url", tool.website),
                "export": {"pick": pick.model_dump(mode="json"), "outcomes": [o.model_dump(mode="json") for o in
                           self.store.list("outcomes", Outcome, pick_id=pick.id)]}}

    def picks(self, business_id: str) -> list[dict]:
        rows = []
        outs = {o.pick_id: o for o in self.store.list("outcomes", Outcome, business_id=business_id)}
        for p in sorted(self.store.list("picks", Pick, business_id=business_id), key=lambda p: p.started_at, reverse=True):
            t = self._tools.get(p.tool_id)
            o = outs.get(p.id)
            rows.append({"pick": p.model_dump(mode="json"), "tool": t.model_dump(mode="json") if t else None,
                         "questions": [{"key": k, "label": l, "unit": u} for k, l, u in QUESTIONS[p.job]],
                         "outcome": {**o.model_dump(mode="json"), "within_interval": o.within_interval} if o else None,
                         "days_since_start": (now() - p.started_at).days})
        return rows

    def checkin(self, pick_id: str, business_id: str, inputs: dict[str, float], note: str = "") -> Outcome:
        pick = self._pick(pick_id, business_id)
        if pick.status not in (Adoption.TRIAL, Adoption.ADOPTED):
            raise Invalid("Check in on a tool you're trying or using")
        allowed = {k for k, _, _ in QUESTIONS[pick.job]}
        clean = {k: float(v) for k, v in inputs.items() if k in allowed and v is not None and math.isfinite(float(v)) and float(v) >= 0}
        if not clean:
            raise Invalid("Report at least one number")
        biz = self.business(business_id)
        est = pick.estimate
        actual = actual_value(pick.job, biz, clean, est.get("margin") or self._margin(biz))
        prev = self.store.list("outcomes", Outcome, pick_id=pick.id)
        keep_id = {"id": prev[0].id} if prev else {}
        out = Outcome(**keep_id, pick_id=pick.id, business_id=business_id, tool_id=pick.tool_id, job=pick.job,
                      days_since_start=(now() - pick.started_at).days,
                      predicted_monthly_usd=est.get("monthly_value") or 0, raw_predicted_monthly_usd=est.get("monthly_value") or 0,
                      predicted_low=est.get("monthly_value_low") or 0, predicted_high=est.get("monthly_value_high") or 0,
                      actual_monthly_usd=actual, reported_inputs=clean, note=note[:500])
        self.store.put("outcomes", out)  # one outcome per pick: re-reporting replaces, never double-counts
        return out

    def _calibration_outcomes(self) -> list[Outcome]:
        return [o for o in self.store.list("outcomes", Outcome) if o.days_since_start >= MIN_DAYS_FOR_CALIBRATION]

    def accuracy(self) -> dict:
        all_outs = self.store.list("outcomes", Outcome)
        return {"rows": published_accuracy(self._calibration_outcomes()),
                "reported": len(all_outs), "eligible": len(self._calibration_outcomes()),
                "min_days": MIN_DAYS_FOR_CALIBRATION,
                "note": "Owner-reported outcomes. Only check-ins at least 14 days after starting count toward calibration."}

    def research(self) -> dict:
        r = research()
        tools = list(self._tools.values())
        ratings = sum(sum(x.count for x in t.ratings) for t in tools)
        reviews = sum(len(t.reviews) for t in tools)
        excluded = sum(1 for t in tools for rv in t.reviews if not rv.relevant)
        return {**r, "stats": {"tools": len(tools), "products": sum(t.kind != "builtin" for t in tools),
                               "builtins": sum(t.kind == "builtin" for t in tools),
                               "platform_ratings_counted": ratings, "reviews_quoted": reviews, "reviews_excluded": excluded,
                               "jobs": {j.value: JOB_LABELS[j] for j in ESTIMATORS}}}
