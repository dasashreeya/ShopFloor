"""Turn an owner's own export files into the numbers the estimators need.

Supported (column names are matched loosely, so exports from different systems work):
  calls     phone-system call log (RingCentral, Google Voice, Grasshopper, Dialpad...): date + status/result
  invoices  QuickBooks/Xero/Jobber invoice list: amount, due date, paid date or status/balance
  orders    POS sales export (Square, Toast, Clover): date + amount/total
Nothing is stored except the computed summary numbers.
"""

import csv
import io
import re
from datetime import date, datetime

TEMPLATES = {
    "calls": "date,time,status,caller\n",
    "invoices": "invoice_number,invoice_date,due_date,paid_date,amount,status\n",
    "orders": "date,total\n",
}
MISSED = re.compile(r"miss|no.?answer|unanswered|voicemail|abandon|declined|not answered", re.I)
ANSWERED = re.compile(r"answer|complete|connect|accepted|inbound call|outbound", re.I)


class ImportError_(ValueError):
    pass


def _find(headers: list[str], *keys: str) -> str | None:
    low = {h: h.lower().strip() for h in headers}
    for k in keys:
        for h, l in low.items():
            if k in l:
                return h
    return None


def _date(v: str) -> date | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    candidates = [v, v.split("T")[0], v.split(" ")[0], " ".join(v.split(" ")[:3]).rstrip(",")]
    for c in candidates:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%b %d, %Y", "%d %b %Y", "%m-%d-%Y", "%B %d, %Y"):
            try:
                return datetime.strptime(c.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _money(v: str) -> float | None:
    v = re.sub(r"[^\d.\-]", "", v or "")
    try:
        return float(v) if v not in ("", "-", ".") else None
    except ValueError:
        return None


def _rows(text: str) -> tuple[list[str], list[dict]]:
    text = text.lstrip("﻿")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    if not rows:
        raise ImportError_("The file has a header but no rows.")
    return list(reader.fieldnames or []), rows


def _span_days(dates: list[date]) -> int:
    return max(1, (max(dates) - min(dates)).days + 1) if dates else 0


def parse_calls(text: str) -> dict:
    headers, rows = _rows(text)
    dcol = _find(headers, "date", "time", "start")
    scol = _find(headers, "status", "result", "disposition", "missed", "answered", "outcome", "type", "action")
    if not dcol or not scol:
        raise ImportError_(f"Need a date column and a status/result column. Found: {', '.join(headers)}")
    dates, missed = [], 0
    for r in rows:
        d = _date(r.get(dcol, ""))
        if d:
            dates.append(d)
        s = (r.get(scol) or "").strip()
        if s.lower() in ("true", "yes", "1") and "miss" in scol.lower():
            missed += 1
        elif MISSED.search(s):
            missed += 1
    if not dates:
        raise ImportError_(f"Couldn't read any dates in column '{dcol}'.")
    days = _span_days(dates)
    n = len(rows)
    return {"metrics": {"calls_per_week": round(n / days * 7, 1), "missed_share": round(missed / n, 3)},
            "summary": f"{n:,} calls over {days} days, {missed:,} missed ({missed / n:.0%}).",
            "rows": n, "columns_used": [dcol, scol]}


def parse_invoices(text: str, today: date | None = None) -> dict:
    today = today or date.today()
    headers, rows = _rows(text)
    acol = _find(headers, "amount", "total", "balance due", "invoice total")
    icol = _find(headers, "invoice date", "date issued", "issue date", "created", "txn date", "date")
    dcol = _find(headers, "due")
    pcol = _find(headers, "paid date", "date paid", "payment date", "paid on", "fully paid")
    stcol = _find(headers, "status")
    if not acol or not dcol:
        raise ImportError_(f"Need an amount column and a due-date column. Found: {', '.join(headers)}")
    amounts, issued, late, judged = [], [], 0, 0
    for r in rows:
        a = _money(r.get(acol, ""))
        if a is not None:
            amounts.append(a)
        if icol and icol != dcol and (d := _date(r.get(icol, ""))):
            issued.append(d)
        due = _date(r.get(dcol, ""))
        paid = _date(r.get(pcol, "")) if pcol else None
        status = (r.get(stcol) or "").lower() if stcol else ""
        if not due:
            continue
        if paid:
            judged += 1; late += paid > due
        elif "overdue" in status or ("paid" not in status and due < today):
            judged += 1; late += 1
        elif "paid" in status:
            judged += 1
    if not amounts:
        raise ImportError_(f"Couldn't read amounts in column '{acol}'.")
    months = _span_days(issued) / 30.4 if issued else None
    n = len(rows)
    metrics = {"avg_invoice": round(sum(amounts) / len(amounts), 2)}
    if months:
        metrics["invoices_per_month"] = round(n / max(months, 1), 1)
    if judged:
        metrics["late_share"] = round(late / judged, 3)
    return {"metrics": metrics,
            "summary": f"{n:,} invoices, average ${metrics['avg_invoice']:,.0f}"
                       + (f", {late}/{judged} paid late ({late / judged:.0%})" if judged else "")
                       + (f", ~{metrics['invoices_per_month']:,.0f}/month" if months else "") + ".",
            "rows": n, "columns_used": [c for c in (acol, icol, dcol, pcol, stcol) if c]}


def parse_orders(text: str) -> dict:
    headers, rows = _rows(text)
    acol = _find(headers, "total", "gross sales", "net sales", "amount", "net total", "collected")
    dcol = _find(headers, "date", "time", "created")
    if not acol:
        raise ImportError_(f"Need an amount/total column. Found: {', '.join(headers)}")
    amounts = [a for r in rows if (a := _money(r.get(acol, ""))) is not None and a > 0]
    dates = [d for r in rows if dcol and (d := _date(r.get(dcol, "")))]
    if not amounts:
        raise ImportError_(f"Couldn't read amounts in column '{acol}'.")
    metrics = {"avg_ticket": round(sum(amounts) / len(amounts), 2)}
    if dates:
        metrics["monthly_revenue"] = round(sum(amounts) / _span_days(dates) * 30.4, 0)
    return {"metrics": metrics,
            "summary": f"{len(amounts):,} orders, average ${metrics['avg_ticket']:,.2f}"
                       + (f", ~${metrics['monthly_revenue']:,.0f}/month" if dates else "") + ".",
            "rows": len(rows), "columns_used": [c for c in (acol, dcol) if c]}


PARSERS = {"calls": parse_calls, "invoices": parse_invoices, "orders": parse_orders}
