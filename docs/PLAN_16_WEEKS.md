# If we had 16 weeks

Goal: go from "a defensible recommendation on day one" to "measured proof that owners who follow ShopFloor get the value we predicted."
Every phase ends with a gate: a measurable result that decides whether we continue, change course, or narrow scope.

| Weeks | Build | Evidence / gate |
|---|---|---|
| **1-2 · Owners first** | Interview 15-20 owners (restaurants, cafés, HVAC/plumbing, landscaping, salons) through UMD's network, SBDCs and SCORE. Shadow 3 businesses for a day. Recruit 8-10 design partners. | Rank jobs by pain × willingness to try × data access. **Gate:** confirm or replace the 4 starting jobs; add 2 (e.g. booking/scheduling, quotes/estimates). |
| **3-4 · Discovery at scale** | Scheduled crawlers for Square App Marketplace, QuickBooks App Store, Xero App Store, Jobber/Housecall Pro marketplaces, Google Workspace Marketplace. Change detection on vendor pricing pages. LLM extraction → human verification queue. | Catalog 100+ tools. **Gate:** spot-check 30 listings: ≥95% correct price/plan fields, 100% working source links. |
| **5-6 · Real data in, no CSVs** | Read-only OAuth connectors: QuickBooks Online, Square, Google Business Profile, Gmail; call-log import from RingCentral/Google Voice. Tenant isolation, consent screens, one-tap disconnect + data deletion. | **Gate:** a design partner connects in <10 min and the computed numbers match their own records. |
| **7-8 · Test the real products** | Vendor sandbox/trial accounts for the top 2-3 tools per job. Run the scenario suite against the **real** product (call it, send it reviews/emails). Expand scenario sets with owners' real anonymized examples. Human graders calibrate the LLM judge. | **Gate:** LLM judge agrees with human graders ≥85%; publish per-tool scenario results with sample sizes. |
| **9-10 · Recommendation quality** | Owner-adjustable assumptions, more hard constraints (languages, hours, compliance), setup-effort estimates from partners, overlap detection across multi-job tools. Fit-score weights tuned on interview data. | Blind test on held-out profiles vs. (a) review-site top-rated, (b) ChatGPT with the same inputs, (c) an SBDC advisor. **Gate:** advisors prefer ShopFloor's shortlist in ≥70% of cases; zero hard-rule violations. |
| **11-12 · Pilot** | 8-10 businesses run a recommended tool for 30+ days with ShopFloor's checklist; weekly check-ins; a holdout week or staggered start where feasible. One two-tool stack with a real hand-off (e.g. AI receptionist → booking → invoice). | **Gate:** ≥6 complete check-ins; record setup time, errors and escalations. Stop any tool that harms customers. |
| **13-14 · Close the loop** | Compare predicted vs. reported value per job; update calibration; publish the accuracy page with real numbers. Join tool logs to POS/accounting records where connectors allow (attribution beyond self-report). | **Gate:** report error and range coverage honestly, including misses. Re-weight or drop assumptions that were wrong. |
| **15-16 · Ready for more users** | Postgres with indexed tenant queries, background job queue for crawls/imports/lab, caching, observability, load tests, WCAG 2.2 AA audit, Spanish UI. Partnerships: SBDC referral flow, chamber of commerce pilots. Business model decision (subscription for owners vs. disclosed, rank-neutral referral fees). | **Gate:** 5 first-time users complete intake → choice → trial unaided; p95 page load <2s at 10× pilot load. |

## Biggest risks and how we'd handle them

- **Vendor data goes stale.** Change detection + "retrieved on" dates on every price; stale listings are flagged automatically.
- **Our value assumptions are wrong.** That's expected: they're labeled, ranged, and corrected per job by check-ins; we publish our error.
- **Pay-to-rank pressure.** Rankings never use referral fees; any fee is disclosed on the tool page.
- **Owners won't connect accounts.** Keep CSV and typed-number paths permanently; ask only for read-only scopes.
- **Self-reported outcomes are noisy.** Move to connector-based attribution (e.g. answered-call → order within 48h) as connectors land.

## Architecture as it scales

Today: FastAPI + SQLite doc store, a JSON catalog, deterministic engine, LLM only for extraction and simulations.
The seams are already there: `discovery.py` (any page → candidate), `engine/intake.py` (any export → metrics; connectors
replace it), `lab/runner.py` `ToolAdapter` (simulated → real vendor adapter), `outcomes/` (self-report → attribution).
Scaling means swapping the store for Postgres, moving crawl/import/lab into a queue, and versioning catalog snapshots
so every recommendation can be reproduced from the exact data it used.
