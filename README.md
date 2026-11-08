# ShopFloor

**Find, compare and adopt AI tools for a small business, scored on that business's own numbers.**

A pizzeria owner, an HVAC tech and a salon owner get *different* answers. ShopFloor asks what software they already
use, what hurts, their budget and a few numbers (or reads their call-log / invoice / sales export). It then ranks real
AI tools on value at their volume, fit with their stack, independent customer evidence, and price transparency.
It also says when **not** to buy: when a free feature they already own does the job, or when their volume is below break-even.

- **18 real tools and built-ins** across 4 jobs (missed calls, review replies, invoice chasing, email), with real plans and prices, trial and contract terms, each linked to its source and dated ([catalog](shopfloor/catalog/tools.json))
- **31 attributed customer reviews** (praise and complaints) and 3,430 platform ratings counted, with off-topic reviews flagged and excluded ([research](docs/RESEARCH.md))
- **Every assumption sourced or labeled** as a ShopFloor assumption ([research.json](shopfloor/catalog/research.json))
- **Evaluation:** 0 of 44 rule-breaking picks vs 13 for a "top-rated" baseline and 23 for "cheapest" ([EVALUATION.md](docs/EVALUATION.md))
- **Adoption loop:** trial → setup checklist → 30-day owner check-in → calibration → published accuracy, plus a clean exit path

## Quickstart

```bash
uv sync
uv run pytest -q                                  # 27 tests, offline
uv run uvicorn shopfloor.api.main:app --reload    # http://localhost:8000
uv run python scripts/evaluate.py                 # regenerates docs/EVALUATION.md
```

With no `OPENROUTER_API_KEY` the app runs on a deterministic offline LLM. The LLM is only used for "Try it on your
example", URL discovery and the scenario lab; **recommendations and all money math never use an LLM**.

## Deploy (judge-accessible link)

- **Render:** New > Blueprint > this repo (uses `render.yaml` + `Dockerfile`). Set `OPENROUTER_API_KEY` (optional).
- **Any Docker host:** `docker build -t shopfloor . && docker run -p 8000:8000 -e OPENROUTER_API_KEY=... shopfloor`
- AI endpoints are rate-limited per IP (`SHOPFLOOR_LLM_PER_HOUR`, default 20). Each visitor gets their own business record (unguessable id).
- It's a PWA: on a phone, "Add to Home Screen" installs it like an app.

## How a recommendation is made

```
owner intake / CSV ─▶ estimators (owner numbers + sourced assumptions) ─▶ job value low/mid/high
                                                                          │
catalog (real plans) ─▶ hard rules (industry, software, budget, must-haves) ─▶ cost at YOUR volume
                                                                          │
                      score = value 40 + fit 25 + evidence 20 + transparency 15
                                                                          │
   per job: use free built-in │ recommend │ don't buy (break-even) │ need data ─▶ budget-optimal stack
                                                                          │
                trial ─▶ checklist ─▶ day-30 owner check-in ─▶ calibration per job ─▶ published accuracy
```

## Layout

```
shopfloor/
  catalog/tools.json       researched tools: plans, terms, ratings, reviews, sources
  catalog/research.json    sourced assumptions, research findings, SBA resources
  engine/estimators.py     job value from owner numbers + labeled assumptions
  engine/pricing.py        cheapest published plan for the owner's volume (overage included)
  engine/recommend.py      hard rules, scoring, no-purchase/built-in logic, budget-optimal stack
  engine/intake.py         CSV import: call logs, invoice lists, POS sales exports
  discovery.py             paste a URL -> LLM-extracted unverified candidate listing
  outcomes/                owner check-ins and Bayesian per-job calibration
  lab/                     scenario tests (simulated vendor behavior, graded by a second model family)
  service.py, api/         orchestration and FastAPI
web/                       zero-build mobile-first PWA
scripts/evaluate.py        persona evaluation vs baselines
docs/                      RESEARCH, EVALUATION, PLAN_16_WEEKS, VIDEO_SCRIPT, ARCHITECTURE
```

## Honest scope

Real today: catalog data, prices, reviews, owner inputs and CSV parsing, the recommender, adoption tracking.
Simulated and labeled as such: "Try it" replies and scenario lab results (vendor behavior on an LLM, not the vendor's product).
Not yet: direct OAuth connectors, vendor sandboxes, scheduled marketplace crawling, measured outcomes from real pilots. See [docs/PLAN_16_WEEKS.md](docs/PLAN_16_WEEKS.md).
