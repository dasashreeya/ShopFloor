# ShopFloor

**We predict the ROI of an AI tool before a small business buys it, and we come back and check whether we were right.**

A business connects what it already uses (Square/Toast, QuickBooks, Gmail, its phone line, Google Business Profile).
ShopFloor has independently crawled POS and accounting marketplaces for AI tools, scored them in a lab on golden-set
tasks, and replays the business's own last 90 days to estimate what each tool would have done. The output is a deck
of cards, one job at a time:

> You missed 214 calls in the last 90 days, 157 of them over the lunch rush.
> RingBack would have recovered roughly 14 orders a month: about +$412/month against $29/month.

Swipe **left** to pass, **up** for a 14-day shadow shift (live data, read-only scopes, no actions), **right** to hire.
**Fire** revokes access, exports the data and cancels billing. Thirty days after a hire we measure what actually happened,
recalibrate every future prediction for that job, and publish our own accuracy.

All LLM calls go through **[OpenRouter](https://openrouter.ai)**.

## Quickstart

```bash
uv sync                                   # Python 3.11+, installs deps into .venv
cp .env.example .env                      # add OPENROUTER_API_KEY (optional, see below)
uv run pytest -q                          # 24 tests, fully offline
uv run python scripts/demo.py --lab       # whole loop in the terminal
uv run uvicorn shopfloor.api.main:app --reload   # UI at http://localhost:8000
uv run python scripts/smoke_openrouter.py # one cheap live call per configured model
```

With no `OPENROUTER_API_KEY`, the app runs on a deterministic `FakeLLM`, so tests, CI and offline demos need no key.
Set `SHOPFLOOR_LLM_MODE=openrouter` to force live calls, or `fake` to force offline.

| Env var | Default | Used for |
|---|---|---|
| `SHOPFLOOR_MODEL_FAST` | `anthropic/claude-haiku-5.5` | simulated tools, listing extraction, card copy, shadow drafts |
| `SHOPFLOOR_MODEL_SMART` | `anthropic/claude-sonnet-5.5` | reserved for harder tasks (agents, crews) |
| `SHOPFLOOR_MODEL_JUDGE` | `google/gemini-3.8-flash` | lab grading (deliberately a different model family from the tools) |

## How the loop works

```
 marketplaces ──crawl──▶ Tool catalog ──golden sets──▶ LabScore (accuracy, p50 latency, $/resolved task)
                                                              │
 connectors ──90 days of Events──▶ replay estimators ◀────────┘
                                          │  × calibration factor (learned from verified outcomes)
                                          ▼
                                   Prediction ──▶ Card ──swipe──▶ pass | shadow (14d) | hire ──▶ fire
                                                                              │
                                              day 30: measure actual ◀────────┘
                                                     │
                                  Outcome ──▶ calibration (per job) ──▶ published accuracy
```

Design rules:
1. **LLMs never compute money.** Estimators are deterministic math over events plus named low/mid/high assumptions.
   An LLM may rephrase card copy, but a rewrite that adds any number not in the facts is thrown away (`deck/cards.py`).
2. **Every assumption is a prior.** Calibration models `log(actual / raw prediction)` per job with a Normal prior.
   The correction factor converges and the interval tightens as hires get verified (`outcomes/calibration.py`).
   `tests/test_learning_loop.py` checks that it recovers a hidden true effect.
3. **Vendors don't submit themselves.** Discovery plugs in `MarketplaceSource`s. Free-text listings are normalized by an LLM
   against a strict JSON schema.
4. **Lab tools are simulated until a vendor gives us a sandbox.** `SimulatedToolAdapter` runs the tool's documented behavior
   on an OpenRouter model. Real adapters implement `ToolAdapter.attempt()`.

## Repo layout

```
shopfloor/
  config.py              settings (.env), model routing, fake/live switch
  llm/                   OpenRouter client (retries, JSON-schema output, usage.cost), FakeLLM
  models.py              domain: Business, Event, Tool, LabScore, Prediction, Card, Hire, Crew, Outcome
  store.py               SQLite JSON doc store (swap for Postgres)
  connectors/            Connector protocol + OAuth scopes; synthetic 90-day history for demos
  discovery/             marketplace crawler + seed listings
  lab/                   golden sets + runner + LLM judge
  replay/estimators.py   per-job ROI math (missed calls, review replies, invoice chasing, email triage)
  deck/cards.py          prediction -> card copy (number-guarded)
  hiring/lifecycle.py    swipe / shadow / promote / fire, crews + event routing
  outcomes/              30-day measurement (Attribution seam) + calibration + published accuracy
  service.py             orchestrates the loop
  api/                   FastAPI app (REST + serves web/)
web/                     zero-build UI on the Google Stitch design: Decision Deck, Active Roster,
                         Outcomes & Lab, Integrations, Tool dossier (drag, buttons, or arrow keys)
design/stitch/           original Stitch export (static mockups + design systems), kept for reference
scripts/                 demo.py, smoke_openrouter.py
tests/
docs/ARCHITECTURE.md     extension points and roadmap
```

## API

| Method | Path | |
|---|---|---|
| GET | `/api/health` | LLM backend, tool count |
| GET | `/api/tools` | catalog with lab scores |
| POST | `/api/crawl` | re-run discovery |
| POST | `/api/lab/{tool_id}` | score a tool on its golden set |
| POST | `/api/businesses` | `{name, connectors?}` onboard (demo: synthetic history) |
| GET | `/api/businesses/{id}` | business |
| GET | `/api/businesses/{id}/deck` | undecided cards, best net ROI first (re-dealt if a newer lab run exists) |
| GET | `/api/businesses/{id}/roster` | hires joined with tool, prediction and outcome |
| GET | `/api/businesses/{id}/tools/{tool_id}/replay` | hour-of-day histogram of when the tool would have acted |
| POST | `/api/cards/{id}/swipe` | `{direction: left\|up\|right}` |
| POST | `/api/businesses/{id}/crew` | `{card_ids}` hire several tools as a crew |
| POST | `/api/hires/{id}/promote` | shadow -> hired |
| POST | `/api/hires/{id}/fire` | revoke + export + cancel billing |
| POST | `/api/hires/{id}/measure` | 30-day outcome vs prediction |
| GET | `/api/accuracy` | published accuracy per job |

## What is stubbed (on purpose)

- **Connectors:** demo businesses use `connectors/synthetic.py`. Real Square/Toast/QuickBooks/Gmail/phone/GBP clients implement `Connector.fetch()`.
- **Outcome attribution:** `SimulatedAttribution` has a hidden true effect per job. The real one joins tool action logs to POS records.
- **Billing and token revocation:** `fire()` marks them done and has TODOs where provider calls go.
- **Marketplace crawling:** `SeedFileSource` reads `discovery/seed_listings.json`. Tool names and vendors there are fictional samples.
