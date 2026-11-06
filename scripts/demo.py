"""End-to-end demo in the terminal: crawl -> lab -> deck -> hire -> measure -> published accuracy.

    uv run python scripts/demo.py            # offline unless OPENROUTER_API_KEY is set
    uv run python scripts/demo.py --lab      # also run the golden-set lab (makes LLM calls)
"""

import argparse

from shopfloor.config import get_settings
from shopfloor.llm import get_llm
from shopfloor.models import SwipeDirection
from shopfloor.service import ShopFloor
from shopfloor.store import Store


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", action="store_true", help="score tools on golden sets")
    ap.add_argument("--businesses", type=int, default=25, help="hires to simulate for the accuracy loop")
    args = ap.parse_args()

    settings = get_settings()
    llm = get_llm(settings)
    sf = ShopFloor(Store(":memory:"), llm)
    print(f"LLM: {type(llm).__name__}  (fast={settings.model_fast}, judge={settings.model_judge})\n")

    tools = sf.crawl()
    print(f"Discovered {len(tools)} tools: " + ", ".join(f"{t.name} [{t.job.value}]" for t in tools))

    if args.lab:
        for t in tools:
            s = sf.run_lab(t.id)
            if s:
                print(f"  lab {t.name:<12} accuracy={s.accuracy:.0%}  p50={s.p50_latency_s:.2f}s  "
                      f"cost/resolved=${s.cost_per_resolved_usd:.5f}  failures={[f['task'] for f in s.failures]}")

    biz = sf.onboard("Luna Taqueria")
    print(f"\nDeck for {biz.name}:")
    deck = sf.deck(biz.id)
    for c in deck:
        print(f"  [{c.tool_name}] {c.headline}\n      {c.body}  (range ${c.monthly_value_low:,.0f}-${c.monthly_value_high:,.0f})")

    top = deck[0]
    hire = sf.swipe(top.id, SwipeDirection.UP)
    print(f"\nShadow shift for {top.tool_name}: {len(hire.shadow_log)} actions it would have taken. Example draft:")
    print("  " + next((e.get("draft", "") for e in hire.shadow_log if e.get("draft")), "(none)"))

    print(f"\nSimulating {args.businesses} businesses hiring and being measured at day 30...")
    for i in range(args.businesses):
        b = sf.onboard(f"Biz {i}")
        card = next((c for c in sf.deck(b.id) if c.job == top.job), None)
        if card:
            sf.measure(sf.swipe(card.id, SwipeDirection.RIGHT).id)
    for row in sf.accuracy():
        print(f"  {row}")


if __name__ == "__main__":
    main()
