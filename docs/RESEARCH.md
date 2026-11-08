# Research

All sources were retrieved on **November 8, 2026**. Machine-readable versions are in
[`shopfloor/catalog/research.json`](../shopfloor/catalog/research.json) (assumptions, findings, SBA resources) and
[`shopfloor/catalog/tools.json`](../shopfloor/catalog/tools.json) (every tool, plan, rating and review with its URL).

## 1. Small-business needs: what the evidence says, and what we built because of it

| Finding | Source | Design decision |
|---|---|---|
| Implementation knowledge, cost and staff capacity are the main barriers to AI adoption; owners also worry about accuracy | [Federal Reserve Bank of SF, 2024 SBCS analysis (Jul 2026)](https://www.frbsf.org/research-and-insights/publications/community-development-research-briefs/2026/07/ai-adoption-in-small-businesses-2024-sbcs/) | Every recommendation shows total cost **at the owner's volume**, trial and contract terms, and a setup checklist |
| 66% of small businesses use AI; 41% use six or more technology platforms | [U.S. Chamber, Empowering Small Business 2026](https://www.uschamber.com/technology/2026-empowering-small-business-report) | Intake starts with the software they already pay for; free built-ins (QuickBooks/Xero reminders, Gemini in Gmail, Google Business Profile) are recommended first |
| SBA advises small trials and measuring value before scaling | [SBA AI guide](https://legacy.sba.gov/business-guide/manage-your-business/ai-small-business) | Adoption = trial → checklist → 30-day check-in; SBA/SBDC/SCORE help is linked in the app |
| 59% of small businesses have invoices 30+ days overdue; average unpaid balance $17.7K | [QuickBooks Late Payments Report 2026](https://quickbooks.intuit.com/r/small-business-data/small-business-late-payments-report-2026/) | Invoice chasing is a first-class job, especially for trades |
| Only 37.8% of calls to small businesses are answered live (411 Locals, 85 businesses); CallRail platform average 28% unanswered | [411 Locals via usecarly](https://www.usecarly.com/blog/missed-call-statistics/), [CallRail via getaira](https://getaira.io/blog/missed-business-calls-statistics) | Missed calls is the default first job; when an owner doesn't know their rate, we use the 28-62% range and say so |

## 2. The platform we're modeled on, and how we differ

[Angi](https://intercom.help/angi/en/articles/11390652-reviews-frequently-asked-questions) combines discovery,
verified reviews and a path to hire. We kept that structure (browse → compare → reviews → engage) and changed three things the brief asks for:

1. **Discovery is ours, not the vendor's.** Vendors don't list themselves; we research them, and the app can ingest any product page as an unverified candidate.
2. **The rating goes beyond reviews.** Reviews are 20 of 100 points. Value at your volume, fit with your stack and price transparency are the rest.
3. **Multiple tools:** a budget-optimal stack, one tool per job, with swaps explained when the budget binds.

## 3. Review study

**Method (decided before collecting):** for each product, the newest visible reviews on platforms that allow access
(Trustpilot, Xero App Store), keeping critical reviews; record author, date, stars, a short verbatim excerpt, theme and
whether it is about the product being sold. G2 and Capterra block automated access and were not used.

**Sample:** 31 reviews quoted across 18 tools and built-ins; 3,430 platform ratings counted; 4 reviews excluded as off-topic (reason shown in the app).

**What we learned:**
- **Platforms disagree.** Chaser and Paidnice score 5.0 on the Xero App Store (98-100% five-star); Birdeye is 3.1 and Podium 4.0 on Trustpilot with far more spread. Marketplace ratings skew positive, so we show each platform separately with its sample size and shrink small samples toward 3★.
- **Ratings are often about something else.** Most Smith.ai Trustpilot reviews describe its human receptionists, and some Goodcall reviews concern an unrelated calling-card service. These are down-weighted or excluded, and the app says so.
- **Cancellation and contracts are the top complaint theme** (Goodcall, Fyxer, Birdeye, Smith.ai). So every card shows the vendor's stated terms, and My Tools has an exit checklist.
- **Several real products have little independent evidence** (Rosie, Shortwave, Jobber Receptionist, NiceJob). We show "thin evidence" rather than inventing a rating.

**Limits:** small, non-random sample; platform verification labels are the platforms' own claims; excerpts were selected to show both sides.

## 4. Assumptions behind the money

Every input in an estimate is tagged **Your number**, **From <file>**, or **Default** (with its grade: peer-reviewed, published, secondary, or ShopFloor assumption).

| Assumption | Value used | Grade | Source |
|---|---|---|---|
| Calls nobody answers (if unknown) | 28% / 40% / 62% | secondary | 411 Locals; CallRail |
| Missed callers who convert when answered | 10% / 20% / 30% | **assumption** | none found; the widely repeated "85% never call back" traces to an uncited vendor blog, so we don't use it |
| Typical HVAC repair ticket | $350 | published | [Angi](https://www.angi.com/articles/how-much-hvac-repair-cost.htm) |
| Restaurant gross margin | 68% (food cost 28-35%) | secondary | [Square](https://squareup.com/us/en/townsquare/food-cost-percentage) |
| HVAC service gross margin | 50% | secondary | [ACHR News](https://www.achrnews.com/articles/91121-analyzing-your-variable-costs) |
| Rating gain from replying to reviews | +0.12★ | peer-reviewed | [Proserpio & Zervas 2017, Marketing Science](https://www.informs.org/News-Room/INFORMS-Releases/News-Releases/Want-to-improve-your-business-s-online-ratings-Make-sure-to-respond-to-reviews) |
| Revenue per +1★ | 5-9% (independent restaurants) | peer-reviewed | [Luca, HBS WP 12-016](https://econpapers.repec.org/RePEc:hbs:wpaper:12-016) |
| Days sooner a late invoice is paid with reminders | 4 (2-8) | secondary | [Xero via business.govt.nz](https://business.govt.nz/news/invoicing-tips-for-prompt-payments) |
| Owner minutes per review reply / late invoice, email time saved, cost of cash | various | **assumption** | labeled in the app; corrected by owner check-ins |

Value is counted as **gross profit or owner time**, never raw revenue: a recovered $32 order at a 68% margin is worth ~$22.

## 5. Acknowledgments

AI tools were used for coding and research synthesis; all sources above were opened and checked by URL.
<!-- Add any faculty/staff/outside coaching here, as the rules require. -->
