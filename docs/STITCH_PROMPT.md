# Google Stitch prompts for the ShopFloor UI

Paste the **master prompt** first, then each **screen prompt** as a follow-up in the same project.
Export as HTML + Tailwind. The field names in brackets match the API (`/api/...`) so the export can be wired up directly.

---

## Master prompt

Design a mobile-first web app called **ShopFloor** for owners of small local businesses (a taqueria, a salon, a hardware store).
These owners are busy, not technical, and suspicious of software that oversells. ShopFloor looks at the business's own last 90 days
of data and recommends AI tools one job at a time, as a swipeable deck of cards. Each card shows how much money that tool
would have made or saved and what it costs. The promise: "We predict the ROI before you buy, and we come back and check whether we were right."

Visual style: calm, warm, trustworthy, like a well-run ledger rather than a flashy fintech app. Off-white paper background,
near-black text, one accent green for money gained and hiring, muted red for passing and firing, amber for the trial ("shadow") state.
Large, clear numbers. Rounded cards with soft shadows. A friendly, legible sans-serif. Plenty of whitespace. No stock photos, no
gradients, no emoji. Use simple line icons and plain text labels for third-party services (no brand logos).

Make it mobile first (390px wide), with a centered single-column layout up to 640px on desktop. Use a bottom tab bar with three tabs: **Deck**, **My Crew**, **Accuracy**.
Every interactive element needs a visible focus state and at least 44px tap targets.

---

## Screen 1: Connect your tools (onboarding)

Header: "Connect what you already use". Subtext: "Read-only to start. We replay your last 90 days; nothing is sent to your customers."
A 2-column grid of connection tiles, each with an icon, a name, what we read, and a Connect / Connected toggle:
Square or Toast (orders), QuickBooks (invoices), Gmail (inbound email), Phone line (call log), Google Business Profile (reviews).
Bottom: a primary button "Deal my cards" (disabled until one tile is connected) and a small link "Use demo data".

## Screen 2: The Deck (main screen)

A stack of cards with the top card fully visible and the next one peeking behind it, slightly scaled down. Top card content:
- Small caps label: job name + tool name, e.g. "MISSED CALLS · RingBack" [job, tool_name]
- Headline (observation, 1–2 lines): "In the last 90 days, you missed 213 calls, 145 of them during the lunch rush." [headline]
- Body (money sentence): "RingBack would have recovered roughly 12 orders a month: about +$358/month against $29/month." [body]
- A money row with two big figures: "+$358 /mo estimated" with a smaller range "$98 – $1,186" underneath [monthly_value_usd, monthly_value_low, monthly_value_high], and "$29 /mo cost" [monthly_cost_usd]
- A chip: "Lab accuracy 80%" [lab_accuracy], plus muted text "Replayed on your last 90 days"
- An expandable "How we got this number" row that reveals the assumptions as label/value pairs (e.g. "Callers who order after a text-back: 25%", "Average ticket: $28.89")

Below the stack are three round buttons with labels: **Pass** (red, ✕, also swipe left), **Shadow 14 days** (amber, half-circle icon, also swipe up),
**Hire** (green, check, also swipe right). Show subtle directional hints at the card edges while dragging: "PASS", "SHADOW", "HIRE".
Also design an empty state: "That's every job we found for you. Check your crew." with a button to My Crew.

## Screen 3: Shadow shift detail

For a tool on its 14-day trial that runs on live data but takes no action. Top: tool name, amber status pill "Shadow · day 6 of 14",
and an info banner: "Nothing was sent. This is what RingBack would have done."
A vertical timeline of would-have actions [shadow_log]: timestamp, event type ("Missed call, 12:14pm"), and an expandable
draft message in a speech-bubble style ("Hi! Sorry we missed your call…") [draft]. A summary stat at the top: "31 actions it would have taken".
Sticky bottom bar: secondary "Fire" and primary green "Hire for $29/mo".

## Screen 4: My Crew

List of hired and trial tools, one row each: tool name, job, status pill (Hired green / Shadow amber / Fired muted) [status],
monthly cost. For hired tools past day 30, show a "Predicted vs actual" mini comparison: "Predicted +$358/mo · Actual +$301/mo",
with a small check if actual was inside the predicted range [predicted_monthly_usd, actual_monthly_usd, within_interval].
Each row has a "Fire" text button. Tapping it opens a confirmation sheet titled "Fire RingBack?" with three checklist lines
(what happens immediately): "Revoke access to Phone line and Square", "Export all its data to you (JSON download)", "Cancel billing ($29/mo)",
then a red "Fire" button and a "Keep" button. Also show a "Hire as a crew" card at the top: "These tools work together. We wire them up."

## Screen 5: Published accuracy

Title: "How right were we?" Subtext: "30 days after every hire we measure what the tool actually delivered and publish it, including when we were wrong."
A table, one row per job: Job, Verified hires [verified_hires], Average error [mape as %], In predicted range [interval_coverage as %],
Current correction [current_correction_factor, e.g. "×0.81"]. Below it, a simple line chart "Our error over time" that falls from about 31% to about 19%
as verified hires grow (x-axis: verified hires, y-axis: average error %). A footnote: "Predictions get sharper as outcomes accumulate."

## Screen 6 (optional): Tool lab report

For a single tool: name, vendor, price, where we found it ("Discovered on Square App Marketplace", since vendors don't submit themselves).
Three stat tiles: Accuracy on test tasks 80%, Typical response time 1.1s, Cost per resolved task $0.0001 [accuracy, p50_latency_s, cost_per_resolved_usd].
A list of failed test tasks with a one-line reason [failures].
