import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shopfloor.catalog import catalog_meta
from shopfloor.config import get_settings
from shopfloor.discovery import DiscoveryError
from shopfloor.engine.intake import TEMPLATES, ImportError_
from shopfloor.llm import LLMError, get_llm
from shopfloor.models import Business, Metrics
from shopfloor.service import Invalid, NotFound, ShopFloor
from shopfloor.store import Store

WEB = Path(os.environ.get("SHOPFLOOR_WEB_DIR") or Path(__file__).resolve().parents[2] / "web")


class IntakeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    industry: str = "other"
    zip: str = ""
    stack: list[str] = Field(default_factory=list)
    budget_usd_month: float | None = Field(None, ge=0)
    needs: dict[str, bool] = Field(default_factory=dict)
    pains: list[str] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)


class UpdateIn(BaseModel):
    name: str | None = None
    industry: str | None = None
    zip: str | None = None
    stack: list[str] | None = None
    budget_usd_month: float | None = None
    needs: dict[str, bool] | None = None
    pains: list[str] | None = None
    metrics: dict | None = None


class DecideIn(BaseModel):
    tool_id: str
    action: str  # trial | adopt | pass


class CheckinIn(BaseModel):
    inputs: dict[str, float]
    note: str = ""


class TextIn(BaseModel):
    text: str = Field(max_length=2000)


class UrlIn(BaseModel):
    url: str = Field(max_length=500)


class RateLimit:
    """Per-IP sliding window for endpoints that spend LLM credits."""

    def __init__(self, per_hour: int):
        self.per_hour, self.hits = per_hour, defaultdict(deque)

    def check(self, request: Request):
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
        q, t = self.hits[ip], time.time()
        while q and q[0] < t - 3600:
            q.popleft()
        if len(q) >= self.per_hour:
            raise HTTPException(429, "Too many AI requests from this device. Try again in a while.")
        q.append(t)


def create_app(sf: ShopFloor | None = None, llm_per_hour: int | None = None) -> FastAPI:
    settings = get_settings()
    sf = sf or ShopFloor(Store(settings.db_path), get_llm(settings))
    app = FastAPI(title="ShopFloor", version="0.2.0")
    app.state.sf = sf
    limit = RateLimit(llm_per_hour or int(os.environ.get("SHOPFLOOR_LLM_PER_HOUR", "20")))

    for exc, code in ((NotFound, 404), (Invalid, 422), (ImportError_, 422), (DiscoveryError, 422), (LLMError, 502)):
        def handler(_: Request, e, code=code):
            msg = f"not found: {e.args[0]}" if isinstance(e, NotFound) else str(e)
            return JSONResponse({"detail": msg}, status_code=code)
        app.add_exception_handler(exc, handler)

    @app.get("/api/health")
    def health():
        return {"ok": True, "llm": type(sf.llm).__name__, "tools": len(sf.tools())}

    # ---- catalog & research ----
    @app.get("/api/catalog")
    def catalog():
        labs = sf.lab_scores()
        return {"meta": catalog_meta(), "tools": [{**t.model_dump(mode="json"), "lab": labs.get(t.id)} for t in sf.tools()]}

    @app.get("/api/catalog/{tool_id}")
    def tool(tool_id: str):
        t = sf.tool(tool_id)
        return {**t.model_dump(mode="json"), "lab": sf.lab_scores().get(tool_id)}

    @app.get("/api/research")
    def research():
        return sf.research()

    @app.get("/api/accuracy")
    def accuracy():
        return sf.accuracy()

    @app.post("/api/tools/{tool_id}/try")
    def try_tool(tool_id: str, body: TextIn, request: Request):
        limit.check(request)
        return sf.try_tool(tool_id, body.text)

    @app.post("/api/lab/{tool_id}")
    def lab(tool_id: str, request: Request):
        limit.check(request)
        score = sf.run_lab(tool_id)
        if score is None:
            raise HTTPException(422, f"no scenario set for {tool_id}")
        return score

    @app.post("/api/discover")
    def discover(body: UrlIn, request: Request):
        limit.check(request)
        return sf.discover(body.url)

    # ---- business ----
    @app.post("/api/businesses")
    def onboard(body: IntakeIn) -> Business:
        return sf.onboard(body.model_dump())

    @app.get("/api/businesses/{business_id}")
    def business(business_id: str):
        return sf.business(business_id)

    @app.patch("/api/businesses/{business_id}")
    def update(business_id: str, body: UpdateIn):
        return sf.update(business_id, body.model_dump(exclude_none=True))

    @app.post("/api/businesses/{business_id}/import/{kind}")
    async def import_csv(business_id: str, kind: str, request: Request):
        raw = await request.body()
        if len(raw) > 5_000_000:
            raise HTTPException(413, "File too large (5 MB max)")
        text = raw.decode("utf-8", errors="replace")
        return sf.import_csv(business_id, kind, text, request.headers.get("x-filename", "upload.csv")[:80])

    @app.get("/api/templates/{kind}.csv")
    def template(kind: str):
        if kind not in TEMPLATES:
            raise HTTPException(404, "unknown template")
        return PlainTextResponse(TEMPLATES[kind], media_type="text/csv",
                                 headers={"Content-Disposition": f"attachment; filename=shopfloor-{kind}-template.csv"})

    @app.get("/api/businesses/{business_id}/recommendations")
    def recommendations(business_id: str):
        return sf.recommendations(business_id)

    @app.get("/api/businesses/{business_id}/tools/{tool_id}")
    def tool_fit(business_id: str, tool_id: str):
        return sf.tool_for_business(business_id, tool_id)

    @app.post("/api/businesses/{business_id}/picks")
    def decide(business_id: str, body: DecideIn):
        return sf.decide(business_id, body.tool_id, body.action)

    @app.get("/api/businesses/{business_id}/picks")
    def picks(business_id: str):
        sf.business(business_id)
        return sf.picks(business_id)

    @app.post("/api/businesses/{business_id}/picks/{pick_id}/adopt")
    def adopt(business_id: str, pick_id: str):
        return sf.adopt(pick_id, business_id)

    @app.post("/api/businesses/{business_id}/picks/{pick_id}/steps/{index}")
    def step(business_id: str, pick_id: str, index: int):
        return sf.toggle_step(pick_id, business_id, index)

    @app.post("/api/businesses/{business_id}/picks/{pick_id}/cancel")
    def cancel(business_id: str, pick_id: str):
        return sf.cancel(pick_id, business_id)

    @app.post("/api/businesses/{business_id}/picks/{pick_id}/checkin")
    def checkin(business_id: str, pick_id: str, body: CheckinIn):
        o = sf.checkin(pick_id, business_id, body.inputs, body.note)
        return {**o.model_dump(mode="json"), "within_interval": o.within_interval}

    if WEB.exists():
        app.mount("/static", StaticFiles(directory=WEB), name="static")
        app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(WEB / "index.html")

        @app.get("/manifest.webmanifest")
        def manifest():
            return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")

        @app.get("/sw.js")
        def sw():
            return FileResponse(WEB / "sw.js", media_type="text/javascript", headers={"Service-Worker-Allowed": "/"})

    return app
