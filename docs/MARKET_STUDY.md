# Market study and user stories

Retrieved November 8, 2026. Market figures are from the sources linked; persona numbers are **composites** built
from those benchmarks for demo and testing, not real businesses.

## 1. How big is the problem?

| Fact | Figure | Source |
|---|---|---|
| U.S. small businesses | ~36.2 million (99.9% of firms); ~6.4 million have employees | [SBA Office of Advocacy, FAQ 2026](https://advocacy.sba.gov/2026/02/03/advocacy-releases-frequently-asked-questions-about-small-businesses-2026/) |
| Restaurant locations | ~750K, roughly 7 in 10 independent / single-unit | [Orbital restaurant data 2026](https://withorbital.com/data/restaurant-industry-statistics/) (cites NRA) |
| Independent restaurants are shrinking | −2.3% locations in 2025 (−9,500) while chains grew 1.4% | Technomic via [FES Magazine](https://fesmag.com/topics/perspectives/this-week-in-foodservice/23426-a-changing-landscape-independents-contract-as-chains-rethink-operations) |
| HVAC contractor businesses | ~120,000 (NAICS 23822) | [IBISWorld](https://www.ibisworld.com/united-states/number-of-businesses/heating-air-conditioning-contractors/1945/) |
| Takeout ordered by phone or in person | 40% (vs 34% app/web) | [William Blair survey via MarketScale](https://www.marketscale.com/industries/food-beverage/diners-cite-inconvenience-before-price-when-cutting-chain-visits-william-blair-finds) |
| Calls to small businesses answered live | 37.8% | 411 Locals, via [usecarly](https://www.usecarly.com/blog/missed-call-statistics/) |
| Small businesses with invoices 30+ days overdue | 59% | [QuickBooks 2026](https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2026/) |
| Small businesses using AI / using 6+ platforms | 66% / 41% | [U.S. Chamber 2026](https://www.uschamber.com/technology/2026-empowering-small-business-report) |
| Top adoption barriers | know-how, cost, staff capacity, accuracy | [Federal Reserve Bank of SF, 2024 SBCS](https://www.frbsf.org/research-and-insights/publications/community-development-research-briefs/2026/07/ai-adoption-in-small-businesses-2024-sbcs/) |

**Takeaway.** The phone is still a primary sales channel for independents, most small businesses miss most calls, and late
invoices hit the majority. Owners already use AI but juggle many tools, and they can't evaluate which new one is worth paying for.

## 2. Who else helps them choose, and the gap

| Option | What it does well | Gap ShopFloor fills |
|---|---|---|
| Angi-style directories | Discovery, reviews, contact a provider | Ratings aren't about *your* volume, budget or stack; vendors list themselves |
| G2 / Capterra | Large review volume | Built for mid-market buyers; no "don't buy", no cost at your usage |
| POS / accounting app marketplaces (Square, QuickBooks, Xero) | Compatible apps, one-click install | Only their own ecosystem; ratings skew positive (we found 5.0 averages) |
| Asking ChatGPT | Fast list of names | No verified current prices per plan, doesn't know what you own, not reproducible |
| SBDC / SCORE advisors | Trusted, free | Limited hours; no live tool catalog (we link to them and would partner) |

## 3. Segments we start with

1. **Independent restaurants and cafés**: phone orders, Google reviews, some catering invoices. Very price-sensitive.
2. **Home-service trades (HVAC, plumbing, landscaping)**: high-value calls ($350+ jobs), many invoices, often already on Jobber/QuickBooks.
3. **Appointment businesses (salons)**: booking calls and reviews; tiny budgets; often need Spanish.

## 4. User stories (personas are composites)

### Maria: family taqueria, College Park, MD
*"I lose lunch-rush calls and I never have time to answer Google reviews. Half my regulars speak Spanish. I can spend maybe $150 a month."*

- Uses: Square POS, Google Business Profile, Gmail, QuickBooks (for catering invoices)
- ~160 calls/week, doesn't know how many she misses; average order $24; ~$48K/month revenue
- ~20 new reviews/month, replies to ~15%; 8 catering invoices/month (~$380), ~40% paid late
- **When** the lunch rush hits, **I want** callers answered in English or Spanish **so I can** keep the order instead of losing it.
- **When** a review comes in, **I want** a polite reply drafted **so I can** look responsive without spending my evenings on it.
- **Acceptance:** only tools that speak Spanish (or say they're unconfirmed), total under $150, free options first.

### Dev: two-truck HVAC company, Silver Spring, MD
*"Every missed call in July is a $350 job going to the next guy on Google. I'm on Jobber and QuickBooks and I'm not adding another login."*

- Uses: Jobber, QuickBooks Online, Google Workspace, Google Business Profile
- ~60 calls/week; average job ~$350 (Angi typical repair); 70 invoices/month (~$620), ~35% late; values his time at $45/h
- **When** I'm on a roof, **I want** urgent calls (no heat, gas smell) transferred to me and the rest booked **so I can** stop losing jobs.
- **When** invoices go late, **I want** reminders to go out automatically **so I can** stop chasing at night.
- **Acceptance:** human hand-off required; prefers tools inside Jobber; free QuickBooks reminders before anything paid.

### Keisha: two-chair salon, Hyattsville, MD
*"I can't pick up when I'm mid-color. I've got $60 a month, tops."*

- Uses: Square, Google Business Profile, Gmail
- ~50 calls/week, ~30% missed; average ticket $85; 6 reviews/month, replies to half; ~2 h/week on email
- **When** I'm with a client, **I want** booking calls answered **so I can** fill tomorrow's chairs.
- **Acceptance:** under $60/month; tells her plainly when something isn't worth it.

## 5. What the stories show in the product

| Persona | Expected behavior (checked in the app) |
|---|---|
| Maria | Spanish-capable receptionist within budget; free "reply yourself" option ranked first, a paid review tool as the swipe-left alternative; QuickBooks reminders first for catering invoices |
| Dev | Jobber Receptionist (in his stack, confirmed hand-off); free QuickBooks reminders and Gemini in Gmail; "don't buy a review tool yet" with break-even |
| Keisha | A $49 receptionist plan fits her volume; everything else either free or "not worth it yet" |
