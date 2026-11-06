# Architecture and extension points

## Seams (swap the stub, keep everything else)

| Seam | Protocol | Stub today | Real implementation |
|---|---|---|---|
| Data in | `connectors.base.Connector.fetch(since, until) -> list[Event]` | `connectors/synthetic.py` | Square Orders API, Toast Orders, QuickBooks Invoices, Gmail, Twilio call logs, GBP reviews |
| Discovery | `discovery.crawler.MarketplaceSource.listings()` | `SeedFileSource` | Scrapers for Square App Marketplace, Toast Partner Connect, QuickBooks App Store |
| Lab | `lab.runner.ToolAdapter.attempt(input) -> LLMResult` | `SimulatedToolAdapter` (OpenRouter) | Vendor sandbox / API adapters |
| Outcomes | `outcomes.measure.Attribution.actual_monthly_usd(hire, pred)` | `SimulatedAttribution` | Join tool action logs to POS/accounting records |
| LLM | `llm.base.LLM.chat(...)` | `FakeLLM` | `OpenRouterClient` |
| Storage | `store.Store` | SQLite JSON docs | Postgres (same collections) |

## Adding a new job (e.g. "no-show reminders")

1. Add a `Job` enum value in `models.py`.
2. Write an estimator in `replay/estimators.py` that returns an `Estimate` with named assumptions and `facts`.
3. Add a card template in `deck/cards.py` and the event kinds in `hiring/lifecycle.JOB_EVENTS`.
4. Add `lab/golden_sets/<job>.json`. Include at least one `MUST_DECLINE` safety task.

## Calibration math

For job *j*, each verified hire gives `r = actual / raw_prediction`. Model `log r ~ N(mu_j, SIGMA^2)` with
`mu_j ~ N(0, TAU^2)`. The posterior mean gives the multiplicative correction `exp(mu_j)`, and the posterior sd widens
the shown interval. With `TAU=0.5, SIGMA=0.4` the first business gets a wide interval, and after ~50 verified hires the
bias is pinned to within a few percent. Learn on the *raw* prediction, never the calibrated one, or the loop only
sees residual bias and drifts back toward 1.

## Roadmap

- Real connectors (Square + Twilio first: they cover the missed-call wedge).
- A per-tool calibration level on top of per-job (hierarchical: tool within job).
- Crews: shared event bus + handoffs between tools (e.g. missed-call texter -> catering inbox).
- Outcome-based pricing once published accuracy is trusted.
