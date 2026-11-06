from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from shopfloor.config import get_settings
from shopfloor.hiring.lifecycle import LifecycleError
from shopfloor.llm import LLMError, get_llm
from shopfloor.models import ConnectorKind, SwipeDirection
from shopfloor.service import NotFound, ShopFloor
from shopfloor.store import Store

WEB = Path(__file__).resolve().parents[2] / "web"


class OnboardIn(BaseModel):
    name: str
    connectors: list[ConnectorKind] | None = None


class SwipeIn(BaseModel):
    direction: SwipeDirection


class CrewIn(BaseModel):
    card_ids: list[str]


def create_app(sf: ShopFloor | None = None) -> FastAPI:
    settings = get_settings()
    sf = sf or ShopFloor(Store(settings.db_path), get_llm(settings))
    if not sf.tools():
        sf.crawl()
    app = FastAPI(title="ShopFloor", version="0.1.0")
    app.state.sf = sf

    @app.exception_handler(NotFound)
    async def _nf(_: Request, e: NotFound):
        return JSONResponse({"detail": f"not found: {e.args[0]}"}, status_code=404)

    @app.exception_handler(LifecycleError)
    async def _lc(_: Request, e: LifecycleError):
        return JSONResponse({"detail": str(e)}, status_code=409)

    @app.exception_handler(LLMError)
    async def _llm(_: Request, e: LLMError):
        return JSONResponse({"detail": str(e)}, status_code=502)

    @app.get("/api/health")
    def health():
        return {"ok": True, "llm": type(sf.llm).__name__, "tools": len(sf.tools())}

    @app.get("/api/tools")
    def tools():
        return [{**t.model_dump(mode="json"), "lab": (s.model_dump(mode="json") if (s := sf.lab_score(t.id)) else None)}
                for t in sf.tools()]

    @app.post("/api/crawl")
    def crawl():
        return [t.model_dump(mode="json") for t in sf.crawl()]

    @app.post("/api/lab/{tool_id}")
    def lab(tool_id: str):
        score = sf.run_lab(tool_id)
        if score is None:
            raise HTTPException(422, f"no golden set for tool {tool_id}")
        return score

    @app.post("/api/businesses")
    def onboard(body: OnboardIn):
        return sf.onboard(body.name, body.connectors)

    @app.get("/api/businesses/{business_id}")
    def business(business_id: str):
        return sf.business(business_id)

    @app.get("/api/businesses/{business_id}/roster")
    def roster(business_id: str):
        sf.business(business_id)  # 404 if unknown
        return sf.roster(business_id)

    @app.get("/api/businesses/{business_id}/tools/{tool_id}/replay")
    def replay(business_id: str, tool_id: str):
        return sf.replay_profile(business_id, tool_id)

    @app.get("/api/businesses/{business_id}/deck")
    def deck(business_id: str):
        return sf.deck(business_id)

    @app.post("/api/cards/{card_id}/swipe")
    def swipe(card_id: str, body: SwipeIn):
        return {"hire": sf.swipe(card_id, body.direction)}

    @app.post("/api/businesses/{business_id}/crew")
    def crew(business_id: str, body: CrewIn):
        return sf.hire_crew(business_id, body.card_ids)

    @app.post("/api/hires/{hire_id}/promote")
    def promote(hire_id: str):
        return sf.promote(hire_id)

    @app.post("/api/hires/{hire_id}/fire")
    def fire(hire_id: str):
        return sf.fire(hire_id)

    @app.post("/api/hires/{hire_id}/measure")
    def measure(hire_id: str):
        o = sf.measure(hire_id)
        return {**o.model_dump(mode="json"), "ratio": o.ratio, "within_interval": o.within_interval}

    @app.get("/api/accuracy")
    def accuracy():
        return sf.accuracy()

    if WEB.exists():
        app.mount("/static", StaticFiles(directory=WEB), name="static")
        app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(WEB / "index.html")

    return app
