# Architecture

```
web/ (PWA, vanilla JS)  ──HTTP──▶  shopfloor/api/app.py (FastAPI, per-IP limits on AI endpoints)
                                          │
                                   shopfloor/service.py
          ┌──────────────┬───────────────┼────────────────┬────────────────┐
   catalog/ (data)   engine/ (pure)   discovery.py      lab/ (LLM)      outcomes/
   tools.json        intake.py        URL → candidate   scenario tests   check-ins +
   research.json     estimators.py    (LLM extraction)  (simulated)      calibration
                     pricing.py
                     recommend.py
                                          │
                                 store.py (SQLite doc store: businesses, picks, outcomes, candidates, lab)
```

## Principles

1. **Deterministic money.** `engine/` is pure Python. No LLM output ever enters a price, value or score.
2. **Catalog is data.** Adding a tool means adding JSON with sources; no code change. Built-in features of software owners already have are first-class entries (`kind: builtin`).
3. **Every number has an origin.** Estimators return `inputs[]` tagged owner / file / default, with grade and sources; the UI shows them.
4. **"No" is an answer.** `recommend_job` can return `use_builtin`, `no_purchase` (with break-even) or `needs_info`.
5. **Tenant isolation.** Every pick/outcome route checks the business id in the path owns the record.

## Extension seams

| Seam | Today | Next |
|---|---|---|
| `discovery.extract(url)` | Paste a URL → unverified candidate | Scheduled marketplace crawls + change detection → verification queue |
| `engine/intake.PARSERS` | CSV call logs, invoice lists, POS exports | OAuth connectors (QuickBooks, Square, Google Business Profile, Gmail) emitting the same metrics |
| `lab/runner.ToolAdapter` | `SimulatedToolAdapter` (documented behavior on an LLM) | Real vendor adapters against sandbox accounts |
| `outcomes/checkin.actual_value` | Owner self-report | Attribution from connector data (answered call → order within 48h) |
| `store.Store` | SQLite JSON docs | Postgres with indexed tenant queries; versioned catalog snapshots |

## Scaling notes

The recommender is O(tools × jobs) per request (~18 × 4 today; fine to thousands). The stack optimizer is exhaustive over
each job's paying options (≤ ~7^4 combinations); beyond ~8 jobs, switch to a knapsack DP. Crawls, imports and lab runs
should move to a background queue. The store's collection scans are the first bottleneck; Postgres with
`(business_id)` indexes fixes it.
