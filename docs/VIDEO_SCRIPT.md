# 10-minute video script

Rubric weights: research 10 · small-business applicability 10 · architecture & scalability 10 · UX 10 · presentation 10.
Every team member must visibly present a section (rubric: "meaningful contributions from each team member").
Replace **[A] [B] [C]** with names.

| Time | Who | What to say | What's on screen |
|---|---|---|---|
| 0:00-0:40 | [A] | "A pizzeria misses ~200 calls a month. There are dozens of AI receptionists from $0 to $599/month. Which one is worth it *for this shop*? Asking ChatGPT gets you a list; it doesn't know your call volume, your budget, or that QuickBooks already chases invoices for free." | Title card, then the For You page |
| 0:40-2:10 | [A] | **Research.** Fed SBCS: barriers are know-how, cost, capacity. Chamber: 41% use 6+ platforms. We read 31 real reviews across 18 tools: platforms disagree (Xero App Store 5.0 vs Trustpilot 3.1); many ratings are about a different product (Smith.ai's human receptionists); cancellation is the #1 complaint. Each finding became a feature. | How we rate tab: research → "So:" rows; a dossier showing an excluded review |
| 2:10-5:10 | [B] | **Live demo.** Intake: industry, software, pains, budget, numbers. Upload a call-log CSV and watch the numbers change. For You: starter stack within budget; Jobber Receptionist for the HVAC shop vs Rosie/Goodcall for the pizzeria; "Turn on QuickBooks reminders first, it's free"; "Don't buy a review tool yet: break-even is 54 reviews/month, you get 8." Open "How we estimated this": each number tagged as yours, a published source, or our assumption. Compare 3 tools side by side. Dossier: real plans, real reviews incl. 1-star, Try-it (labeled simulation). Start trial → checklist → check-in → cancel with exit steps. Show it on a phone (PWA). | Screen recording of the live link; switch between Pizzeria and HVAC examples to prove recommendations differ |
| 5:10-6:10 | [B] | **Why the recommendations are good.** Hard rules before scoring; value at *your* volume using real plan + overage pricing; evidence shrunk when thin; free built-ins and "don't buy" are allowed answers. Evaluation on 11 personas: 0/44 rule-breaking picks vs 13 for top-rated, 23 for cheapest; 0 vs 16 ignored free built-ins. | docs/EVALUATION.md table |
| 6:10-7:10 | [C] | **Architecture & scale.** Deterministic engine (LLMs never compute money); catalog as data; seams for crawlers, connectors, real vendor adapters, attribution; per-IP rate limits; PWA. 27 automated tests. What breaks at 10× and the fix (Postgres, job queue, versioned catalog snapshots). | README diagram, file tree, test run |
| 7:10-9:10 | [C] | **16 weeks.** Walk the table in PLAN_16_WEEKS.md: interviews → crawlers → OAuth connectors → test real vendor products → blind test vs ChatGPT and an SBDC advisor → 30-day pilot with 8-10 businesses → publish real accuracy. Name the gates. | PLAN_16_WEEKS.md table |
| 9:10-9:40 | [A] | **Honest scope.** Real: prices, reviews, owner numbers, CSV import, recommender. Simulated and labeled: try-it replies and scenario lab. Not yet: OAuth, vendor sandboxes, measured pilot outcomes. Acknowledge AI assistance and any coaching. | "What's real today" card in How we rate |
| 9:40-10:00 | all | Link + 3-step test instructions for judges: open link → tap "HVAC shop (example numbers)" → open any tool. | Link on screen |

## Judge test instructions (put in the submission)

1. Open the link (works on phone or laptop; no login).
2. Tap **HVAC shop (example numbers)**, then **Pizzeria**: the recommendations differ. Or enter your own.
3. Tap any tool name for real prices, reviews and sources. Try **Browse → Compare** and **Start a trial → My tools**.

## Likely judge questions

- *Why not just ask ChatGPT?* It has no reliable current price per plan at your volume, doesn't know what you already own, and can't be checked. Ours is reproducible, cites every number, and says "don't buy." The 16-week plan includes a blind test against ChatGPT.
- *Did you test the vendors' products?* Not yet. Try-it and the lab simulate their documented behavior and are labeled that way. Weeks 7-8 test the real products.
- *Where do the dollar figures come from?* Your numbers × labeled assumptions, shown per card. Profit and time, not revenue.
- *Has anyone saved money?* We haven't run a pilot yet; the accuracy page is empty on purpose until owners check in.
- *How does it use SBA offerings?* SBDC/SCORE/Learning Platform links on every recommendation page, and SBDC advisors are part of the validation and distribution plan.
