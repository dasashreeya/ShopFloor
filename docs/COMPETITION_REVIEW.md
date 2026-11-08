# ShopFloor competition review — November 8, 2026

> Historical review of the original prototype, before the catalog, recommendation, intake, and adoption upgrades. Findings and test results below describe that earlier version. See [README.md](../README.md) and [EVALUATION.md](EVALUATION.md) for the updated implementation and evaluation.

The concept can compete. The current implementation is a promising prototype, but its research evidence, tool discovery, and recommendation validation are too thin to call it a strong winning submission yet. Keep the predict–try–verify concept. Put the remaining effort into credible evidence and recommendation quality before adding more visual polish.

This review covers the application source, API, frontend, tests, configuration, scripts, architecture documentation, and design prompts. The Stitch exports are reference designs rather than additional implemented product features. External sources below were consulted on November 8, 2026. No owner interviews or vendor-product trials were conducted in this review. Frontend observations are based on source inspection and the previously confirmed local launch; this is not a completed accessibility or usability study. Application source was not changed during the review.

**What works and deserves presentation time**

- The product organizes recommendations around business jobs and a concrete economic decision.
- ROI calculations are deterministic; LLMs rewrite observations and draft actions rather than calculate money.
- The catalog, lab, replay, lifecycle, and outcome components form an executable end-to-end loop.
- Trial-before-adoption and an exit path address an owner's fear of expensive, irreversible software decisions.
- Tests exercise the HTTP flow, lifecycle, estimator math, retries, and learning behavior in simulation.
- The interfaces for discovery sources, connectors, tool adapters, and attribution give a sensible path to replacing stubs.

**Assessment against the actual rubric**

These are review judgments, not predicted judge scores. Presentation quality and competing teams are unknown.

| Criterion | Current assessment | What would materially improve it |
|---|---|---|
| Research, 10 points | Weak evidence in the repo. No sourced owner research, customer-review corpus, or documented competitor study. Estimator priors are not tied to studies. | Show a small documented research sample, traceable reviews, limitations, and the specific decisions research changed. |
| Small-business applicability, 10 points | Clear restaurant use case and familiar software names; all actual histories are synthetic and no provider is connected. | Let an owner specify needs, budget, existing stack, and constraints. Show one genuine data import and a feasible adoption path. |
| Architecture and scalability, 10 points | Good modular MVP design; expensive work is synchronous, persistence scans collections, and public-service controls are absent. | Explain queued jobs, tenant isolation, versioned evidence, idempotent actions, and durable storage. Demonstrate a reliable narrow flow now. |
| User experience, 10 points | Coherent task flow and keyboard/button alternatives; little first-time guidance, comparison, provenance, or owner control. | Add visible action labels, business intake, comparison, explanations, evidence status, and test with first-time users. |
| Presentation, 10 points | Not assessable without the video. | Give research, live demonstration, measured validation, honest scope, all members' contributions, and a concrete 16-week plan. |

The eligibility requirements also need a separate team check: two or three members, one team per student, and in-person availability on November 17. A locally running app does not fulfill the judge-accessible prototype-link deliverable. No public deployment URL or deployment configuration was found in the reviewed repo; a deployment may exist elsewhere.

**The central credibility problem**

The README leads with a claim that the platform has independently crawled marketplaces and scored tools. In this implementation:

- `shopfloor/discovery/crawler.py` reads `SeedFileSource`, which loads a local JSON file. There is no HTTP marketplace crawler.
- `shopfloor/discovery/seed_listings.json` contains six fictional/sample listings, including RingBack and DueNudge. Prices are examples, not verified market prices. One listing exercises LLM extraction.
- `ShopFloor.history()` always calls the restaurant-focused synthetic generator. The UI creates Joe's Pizza automatically.
- The lab runs the same underlying fast model with a tool-description prompt. It does not execute the named vendor's product. A second model grades that simulation.
- There are 12 unique golden tasks: missed calls 5, review replies 3, invoice chasing 2, email triage 2. Those are useful initial examples, not a reliable estimate of vendor accuracy. Different jobs use different tasks; a global cross-job leaderboard is not a fair common benchmark.
- Shadow logs are generated once from historical synthetic events. They are not a live 14-day integration.
- Hire, billing cancellation, and scope revocation update local records; provider calls are TODOs.
- Day-30 results come from `SimulatedAttribution`, whose outcomes are generated from a chosen hidden ratio and random noise. Learning-loop tests establish behavior under that simulator, not measured customer value.
- Crew routing stores event-to-hire IDs. There is no deployed cross-vendor workflow or UI for assembling and validating a crew.

These are reasonable hackathon seams. Make their status prominent. Use labels such as sourced listing, vendor claim, simulation benchmark, synthetic business data, and simulated outcome. Do not describe simulated results as verified commercial performance.

**What the recommendation engine actually does**

`ShopFloor.predict()` checks that the tool's integration list is a subset of the business's connector list. It estimates value using a job-specific formula and either a lab pass rate or a default accuracy of 0.7. `deck()` keeps the tool with the highest estimated monthly value minus subscription cost for each job, then sorts those winners by that amount.

This is a substantive starting point beyond a conversational list of tools. Its weaknesses are in the inputs, missing constraints, and validation:

- No owner goal, monthly budget, language, company size, risk tolerance, implementation capacity, or existing equivalent feature enters ranking.
- Tools within a job share an economic model even when their mechanisms differ, such as an SMS text-back tool versus a voice order-taking tool.
- Passing a text task is treated as a multiplier on business outcomes. That relationship has not been demonstrated.
- Integration fields conflate required prerequisites, optional compatible software, and alternative supported platforms.
- The engine does not check evidence freshness, actual integration availability, support quality, contract terms, usage charges, or setup costs.
- It has no no-purchase decision and no portfolio budget or overlap calculation for multiple tools.
- Cards hide alternative products. Owners cannot properly compare the selected tool with an excluded competitor or an existing built-in feature.
- The UI does not display the stored prediction assumptions. A busy owner cannot inspect or change the recovery-rate or hourly-value assumptions behind the estimate.

**Confirmed defects and limitations**

The additional probes below used isolated in-memory stores and fake LLMs. They did not change the running demo's records or spend API credits.

| Priority | Finding and evidence | Relevant location / remedy |
|---|---|---|
| High | An all-fail lab result makes both the lab response and subsequent `/api/tools` response return HTTP 500. Cost per resolution is stored as infinity, which the HTTP JSON response cannot serialize. | `shopfloor/lab/runner.py:95`. Use a JSON-safe unavailable value and expose the failure status. |
| High | Testing a competing tool does not invalidate the incumbent card. Probe: RingBack remains selected at $496 estimated net while the newly scored CallCatch would produce $671 under the same explicitly constructed fixture. These are test-fixture amounts, not market results. | `shopfloor/service.py:91`. Version the candidate set and all ranking inputs per job. |
| High | A business with zero history still receives a paid recommendation. Gmail-only probe with an empty history returned InboxHost at negative $15/month estimated net. | `shopfloor/service.py:96`. Add insufficient-data and no-purchase outcomes. |
| High | The same newly hired tool can be measured immediately and repeatedly; two requests create two outcomes for one hire. This inflates the published verified-hire count and calibration weight. | `shopfloor/service.py:195` and `shopfloor/outcomes/measure.py:32`. Make simulated time explicit and real measurements unique by hire and observation window. |
| High before public access | There is no authentication, tenant authorization, or rate/spend control. A cross-business crew probe creates a crew for business A containing a hire belonging to B. Costly lab endpoints are public to anyone who can reach the server. | `shopfloor/api/app.py` and `shopfloor/service.py:152`. Isolate judge sessions, validate ownership, and cap or restrict live lab work. |
| Medium | An empty connector list becomes all connectors because onboarding uses `connectors or list(ConnectorKind)`. A Gmail-only business's history also contains POS, phone, review, and invoice events. | `shopfloor/service.py:51` and `:69`. Distinguish omitted input from an empty list and filter/import by connected source. |
| Medium | The existing refresh test failed: strict timestamp comparison can miss a lab run created at the same timestamp as the prediction. In six follow-up probes, five produced an equal timestamp and no refresh. | `shopfloor/service.py:94`. Use explicit revisions rather than wall-clock ordering. |
| Medium | Updated calibration alone does not invalidate existing cards. Updating an alternative candidate has the separate invalidation problem described above. | `shopfloor/service.py:91`. Track model, data, catalog, and calibration versions. |
| Medium | Crew hiring performs several writes without a transaction; a later invalid card can leave earlier hires active. No bundle overlap or double-counting adjustment is made. | `shopfloor/service.py:152`. Validate the entire request before an atomic commit. |
| Medium | Low/mid/high assumptions widened by uncertainty about bias are shown as a 90% range. Predictive coverage has not been established; uncertainty about an individual future business differs from uncertainty about mean bias. Zero/negative outcome ratios are excluded from calibration. | `shopfloor/outcomes/calibration.py:24` and `:31`. Label scenario ranges honestly and evaluate coverage including failures. |
| Medium | Missed-call value is gross order revenue, while other estimators mix time value, collections effects, and revenue. None constitutes a consistent estimate of incremental profit. Labor saved may be capacity rather than cash savings. | `shopfloor/replay/estimators.py`. Separate revenue, contribution margin, time, cash flow, and costs. |
| Medium | Read-only access is inferred by searching scope names for `read`. Provider scopes do not always encode their true permissions that way. | `shopfloor/hiring/lifecycle.py:25`. Define provider-specific permission capabilities when implementing real connectors. |
| Lower | UI says discovery crawled marketplaces, reads live data, and shows verified actuals despite the simulation seams. Run Lab ends with a success toast even after caught tool failures. A failed refresh can also leave the swipe guard set. | `web/app.js`. Add explicit evidence states, partial-failure feedback, and `finally` cleanup. |
| Lower | Tool URLs are not preserved by the normalizer even though the model has `listing_url`; there are no source links in the dossier. Global calibration is shared across all demo businesses. | `shopfloor/discovery/crawler.py:61`, `web/app.js`, and `ShopFloor.accuracy()`. Keep provenance and separate demo from production evidence. |

**Verification performed**

The full existing test command was `.venv\Scripts\python.exe -m pytest -q`. Result: **23 passed, 1 failed**, specifically `test_lab_run_refreshes_undecided_cards_only`. The timestamp probes explain the observed failure on this Windows environment. This review does not claim the suite is green.

Earlier launch verification established HTTP 200 for the UI and an OpenRouter-backed health response with six tools. The browser requested the business, tools, roster, accuracy, and deck endpoints successfully. Two small live schema-mode calls succeeded for the fast and judge models. Those checks establish API connectivity, not vendor-tool performance. Pytest was installed into the ignored local virtual environment for this review.

**Research that can strengthen the submission**

Angi is a reference for discovery, comparison, trusted evidence, and a route to engagement. Its review process includes automated verification and follow-up in some circumstances. Borrow the evidence and decision structure; the competition explicitly asks for more than user ratings. [Angi review process](https://intercom.help/angi/en/articles/11390652-reviews-frequently-asked-questions)

The Federal Reserve's July 2026 qualitative analysis of the **2024** Small Business Credit Survey identifies implementation knowledge, financial cost, and staff capacity as barriers, alongside accuracy concerns. This supports showing setup effort, total cost, and controlled trials. It is a distinct sample and period from other adoption surveys. [Federal Reserve analysis](https://www.frbsf.org/research-and-insights/publications/community-development-research-briefs/2026/07/ai-adoption-in-small-businesses-2024-sbcs/)

The SBA advises businesses to begin with small trials and assess value. A relevant SBA learning-resource link and practical deployment checklist would fit the rubric better than displaying an SBA logo without functionality. [SBA AI guidance](https://legacy.sba.gov/business-guide/manage-your-business/ai-small-business)

The Chamber's October 2026 report says 66% of surveyed small businesses use AI and 41% use six or more technology platforms. Those findings motivate evaluating incremental value and compatibility with existing software. They do not prove that AI caused business growth or that ShopFloor works. [Chamber report](https://www.uschamber.com/technology/2026-empowering-small-business-report)

Examples of attributable customer feedback found during this review:

| Source and context | Paraphrased evidence | Product/research implication |
|---|---|---|
| Chaser, Xero App Store; Jennifer Lee and Alex Irving reviews | Reviewers describe useful scheduling, customer email tracking, and time savings; one compares the product with Xero's existing reminders. The listing describes AI features. | Include the owner's existing built-in automation as a comparison baseline. A positive review alone is not incremental-value evidence. [Reviews](https://apps.xero.com/us/app/chaser/reviews), [product listing](https://apps.xero.com/us/app/chaser) |
| Slang AI, G2; Kanhaiya Kumar B., December 7, 2025 | Reports useful routine call handling, while noting repeated speech for some accents or fast speakers and a need for monitoring. G2 marks this reviewer organic/validated; the stated industry is software rather than restaurant operation. | Test speech and escalation on the actual vendor product before making voice-quality claims; record reviewer relevance. The existing text simulator cannot test accents. [G2 reviews](https://www.g2.com/products/slang-ai/reviews) |
| Smith.ai, Trustpilot; Kyle Todd, October 9, 2026, and company reply updated October 14 | Reviewer reports cancellation difficulty; the company says cancellation was confirmed and describes a 30-day cancellation policy. Another reviewer, John J. Sheehan, praises service responsiveness. | Preserve both favorable feedback and criticism with the vendor response. Show contract/exit terms rather than promise universal immediate cancellation. [Trustpilot reviews and responses](https://www.trustpilot.com/review/smith.ai) |

These are publicly attributable reports, not independently authenticated experiences or a representative research sample. Platform verification labels must remain platform claims. Some G2 entries are incentivized or from guest/non-business users, and some appear poorly matched to restaurant phone answering; filter them rather than treating all reviews equally. Avoid relying on a review site's AI-generated summary as if it were an original customer review. Product-level reviews may also cover a human receptionist offering rather than the exact AI plan being compared.

For a defensible small study, define the sampling rule before reading: for example, the newest accessible relevant reviews for each shortlisted product, retaining positives, criticisms, and disconfirming evidence. Record product/plan, source URL, date when available, reviewer role/industry, verification and incentive labels, use case, benefits, problems, and your interpretation. Report the actual sample size and missing fields. Do not invent dates or inflate a few examples into a validated research corpus.

If time permits, interview three to five actual owners. Ask which software they already pay for, what task repeatedly costs time or loses sales, how they judge software value, what setup they can tolerate, and what would stop them adopting. Record consent and anonymized notes. Report small-sample limitations. No interviews have been completed as part of this review.

**A recommendation engine worth defending**

Use an explicit pipeline with traceable inputs:

1. Capture owner needs: industry, task volumes, current stack, budget, languages, setup capacity, and desired outcomes. Offer manual entry or a CSV path so OAuth is not a prerequisite to trying the product.
2. Discover real candidates from a small number of supported sources. Preserve fetched evidence, URLs, retrieval time, extraction results, and source-specific limitations. Fetching a supplied listing is ingestion; claim discovery only when the platform actually enumerates/finds candidates.
3. Apply hard constraints first: product availability, relevant capability, required integration, budget, language, and human escalation. Unknown compatibility should be shown as unknown rather than assumed compatible.
4. Assess quality within the relevant job. Separate sourced customer experience, vendor claims, simulation tests, and actual vendor-product benchmarks. Give sample size and uncertainty.
5. Estimate incremental benefit with adjustable assumptions. Separate contribution profit, time/capacity, cash-flow effects, subscription, usage, setup, and maintenance costs. Include the existing software/no-purchase baseline.
6. Rank eligible candidates using the economic estimate and explicit feasibility/evidence criteria. Avoid decorative weighted scores whose weights have not been tested. Show the top alternatives, disqualifications, assumptions, and an insufficient-evidence result.
7. For bundles, respect a total budget, avoid duplicate capabilities and overlapping benefits, and show an actual handoff. Do not sum every tool's standalone benefit.
8. Learn from distinct, well-defined observation windows. A matched historical order is evidence of association, not automatically causal incremental revenue; use holdouts or a staged comparison where feasible.

An LLM can extract evidence and explain choices. The source records, constraint checks, calculations, evaluation, and adoption workflow make the product defensible. A different model family as judge is a useful design choice, but it does not establish independent vendor testing or human-level grading reliability.

**How to demonstrate that recommendations are good**

Create a fixed set of 10–15 business profiles before tuning: a low-call-volume restaurant, a high-volume restaurant, a trade business with late invoices, a business with a tiny budget, one with no usable data, and one whose current software already solves the task. If a vertical is unsupported, test and expose that limitation instead of fabricating support.

Compare ShopFloor with a simple price/star-rating baseline and a generic assistant given the same business information. Also consider a stronger source-enabled assistant with equivalent evidence access. Blindly review the recommendations against a human-defined rubric. Keep tuning examples separate from held-out profiles.

Measure constraint violations, relevant top-three choices, unsupported factual claims, source coverage/freshness, and the time/assistance needed to choose and explain a tool. For any numeric success claim, show the actual numerator, denominator, examples, and limitations. Proposed release gates are zero hard-constraint violations in the fixture set, cited key product claims, and successful completion of core flows by at least four of five first-time testers. These are proposed gates, not achieved results.

**Priority before the November 8, 11:59 p.m. submission**

1. Correct the credibility labels throughout the UI, README, and video. Keep the scope narrow and accurate. Avoid presenting simulated savings as proof of commercial value.
2. Replace the decision-facing fictional catalog with a manageable shortlist of real products, ideally six to ten across the chosen tasks, with current sources, plan costs or honest quote-required status, compatibility evidence, and engagement links. Add one working candidate-discovery source if feasible. Preserve demo fixtures separately.
3. Add a compact business intake and side-by-side alternatives. Show budget, existing software, reasons, assumptions, and a no-purchase result. Keep restaurants as the primary wedge; only add a second vertical if its behavior is real and tested.
4. Fix the confirmed recommendation refresh, all-fail lab serialization, duplicate audit, and ownership issues. Make the current test suite pass and add focused checks for these demonstrated failures.
5. Demonstrate one real data path: an owner-provided/anonymized CSV import or a read-only sandbox connector. Label sandbox data appropriately. A CSV path is more feasible tonight than six OAuth integrations.
6. Add a short sourced research panel/document and a small measured recommendation evaluation. A few credible, completed observations beat unexecuted claims about a large study.
7. Publish a stable judge-accessible demo with isolated sessions, persistent availability, a reset path, and bounded API spend. Test from a signed-out browser/device. The current localhost URL is insufficient. Do not expose the shared key or unrestricted live lab calls.
8. Rehearse and record the video. Leave upload and link-permission time before the deadline. Do not spend the last hour on another visual redesign.

If time is short, preserve credibility, a working public flow, real evidence, and clear recommendation reasoning before attempting broad vendor automation. Full billing control, causal ROI validation, six integrations, and several mature verticals belong in the 16-week plan.

**A concrete 16-week plan**

All quantities and targets below are proposed work, not completed results or promised outcomes.

| Weeks | Work and deliverable | Evidence / decision gate |
|---|---|---|
| 1–2 | Interview roughly 12–15 owners across restaurants and home services; examine existing workflows and software costs; recruit design partners. | Select one initial job from observed pain, willingness to try, and accessible data. Document reasons for excluding other jobs. |
| 3–4 | Build provenance-backed discovery for one or two sources, with change detection, normalization, deduplication, and review metadata. | Audit a sample of listings for factual accuracy, working links, freshness, and compatibility. |
| 5–6 | Implement one real read-only connector and CSV fallback; establish tenant isolation, consent, deletion, and event normalization. | A design partner can import/reconcile data and disconnect access successfully. |
| 7–8 | Add real vendor adapters where APIs/sandboxes allow; assemble job-specific test sets and human-grading guidance; version benchmark inputs. | Compare automated grading with human judgments. Publish limitations for tools that cannot be directly tested. |
| 9–10 | Build constrained recommendations, alternatives, total costs, no-purchase outcomes, and owner-adjustable assumptions. | Held-out profile evaluation against simple ranking and source-enabled assistant baselines. |
| 11–12 | Pilot controlled shadow trials with several consenting businesses; measure owner effort, errors, and escalation. Test one genuine two-tool handoff. | Review failures with owners before enabling any customer-facing action. Trials begun earlier can contribute longer follow-up here. |
| 13–14 | Measure eligible outcomes with distinct windows, baseline comparisons, and overlap controls; evaluate calibration on held-out observations. | Report uncertainty and failures; do not claim statistically established causal ROI from a small pilot. |
| 15–16 | Complete usability/accessibility work, load/failure tests, queued jobs, operating-cost measurement, and deployment/runbooks. Publish pilot findings and the next scope decision. | Demonstrate that owners can make and explain a choice, safely begin a supported deployment, and exit. Decide whether evidence supports expansion. |

For scale, keep the modular service boundaries but replace collection-wide Python filtering with indexed tenant queries, move lab/import/crawl work into bounded queues, record immutable evidence and model versions, and add task retries and observability. SQLite is a reasonable local MVP choice; changing databases alone will not solve ownership, concurrency, or long-running work. Referral commissions should be disclosed and excluded from ranking logic; the current 20% referral-fee field creates a foreseeable trust question.

**The 10-minute video**

| Time | Content | Evidence on screen |
|---|---|---|
| 0:00–0:40 | A concrete owner decision and why choosing software is difficult. | One actual sourced research observation or consented interview finding. |
| 0:40–1:40 | Research method, sample, Angi comparison, and what changed because of findings. | Source table and one favorable/one critical review, with limitations. |
| 1:40–4:40 | Live flow: business intake, evidence-backed shortlist, comparison, explanation, trial preview, and exit path. | The actual working prototype; label every simulated step. Include an excluded tool or no-purchase case. |
| 4:40–5:40 | Explain the recommendation logic and why the chosen tool differs for two profiles. | Constraints, actual assumptions, alternative, and source links. |
| 5:40–6:40 | Evidence the approach works technically and helps a user decide. | Real import/API result, actual test outcomes, and measured evaluation. Avoid presenting code tests as proof of customer ROI. |
| 6:40–8:40 | The 16-week plan and biggest technical/product risks. | Milestones, pilot design, measurement gates, and connector/adapter roadmap. |
| 8:40–9:25 | Current scope, limitations, contributions from every member, and coaching/tool acknowledgments. | Explicit implemented/simulated/planned matrix and names with concrete contributions. |
| 9:25–10:00 | State what is proven, what will be validated next, and how judges can test. | Public link and short test instructions. |

**Questions to prepare for**

- Why not ask a general assistant? Answer with reproducible constraints, evidence, comparisons, and a measured baseline result. Do not claim assistants cannot access current sources or business data.
- Did you actually test the vendor product? For the current code, the answer is no: it tests an LLM simulation of a behavior description. Explain exactly what that proves and what a real adapter would add.
- Where do the dollar estimates come from? Show observed inputs separately from explicit assumptions; explain whether the output is revenue, capacity value, cash flow, or profit.
- Did anyone save this money? Current outcomes are simulated. Do not imply 30 days of field evidence were gathered during a weekend.
- Can you really cancel another vendor immediately? Current cancellation is a local simulation. Vendor contracts and APIs determine the real process.
- Why start with restaurants? A specific validated workflow can be a credible first market. Show how event normalization and job-specific models support expansion rather than claiming every vertical works today.
- What did each teammate do? Give concrete research, implementation, evaluation, and presentation contributions with acknowledgments required by the rules.

The most useful positioning is: **ShopFloor helps an owner choose a tool using traceable evidence, their business constraints, and a controlled path to adoption; the longer-term loop checks whether the expected value appears.** Make the evidence behind that sentence visible in the prototype and video.
