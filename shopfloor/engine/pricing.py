"""What a tool would actually cost *this* business per month, from the vendor's published plans."""

from dataclasses import dataclass

from shopfloor.models import Tool


@dataclass
class Cost:
    usd_month: float | None  # None = quote only / unknown
    plan: str
    note: str = ""


def monthly_cost(tool: Tool, usage: dict[str, float]) -> Cost:
    p = tool.pricing
    if p.quote_only or not p.plans:
        return Cost(None, "Quote required", "Vendor does not publish prices")
    unit = p.unit
    label = unit.replace("_", " ")
    qty = usage.get(unit, 1.0) if unit not in ("flat", "locations") else 1.0
    best: Cost | None = None
    fallback: Cost | None = None
    for plan in p.plans:
        if plan.included is None or unit in ("flat", "locations"):
            c = Cost(plan.usd_month, plan.name)
        elif unit == "users":
            extra = max(0.0, qty - plan.included)
            per = plan.overage if plan.overage is not None else plan.usd_month
            c = Cost(plan.usd_month + extra * per, plan.name, f"{int(qty)} user(s)" if qty > 1 else "")
        elif qty <= plan.included:
            c = Cost(plan.usd_month, plan.name, f"~{qty:,.0f} {label}/mo fits the {plan.included:,.0f} included")
        elif plan.overage is not None:
            over = (qty - plan.included) * plan.overage
            c = Cost(plan.usd_month + over, plan.name,
                     f"~{qty:,.0f} {label}/mo: {plan.included:,.0f} included + ${over:,.0f} overage")
        else:
            fallback = Cost(plan.usd_month, plan.name,
                            f"~{qty:,.0f} {label}/mo exceeds the {plan.included:,.0f} included; overage price not published")
            continue
        if best is None or c.usd_month < best.usd_month:
            best = c
    return best or fallback or Cost(None, "Unknown", "No plan fits")
