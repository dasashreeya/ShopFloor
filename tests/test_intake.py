from datetime import date

from shopfloor.engine.intake import parse_calls, parse_invoices, parse_orders


def test_call_log_from_a_phone_system_export():
    rows = [f"2026-10-{d:02d},12:0{i},{'Missed' if i % 4 == 0 else 'Answered'},+1301555000{i}"
            for d in range(1, 15) for i in range(8)]
    r = parse_calls("Date,Time,Result,From\n" + "\n".join(rows))
    assert r["metrics"]["calls_per_week"] == 56.0 and r["metrics"]["missed_share"] == 0.25


def test_invoice_export_detects_late_payments():
    csv = ("Invoice #,Invoice Date,Due Date,Date Paid,Amount\n"
           "1,09/01/2026,09/15/2026,09/14/2026,$500.00\n"
           "2,09/10/2026,09/24/2026,10/10/2026,\"$1,000.00\"\n"
           "3,10/01/2026,10/15/2026,,300\n")
    r = parse_invoices(csv, today=date(2026, 11, 8))
    assert r["metrics"]["late_share"] == round(2 / 3, 3)
    assert r["metrics"]["avg_invoice"] == 600


def test_pos_orders_export():
    r = parse_orders("Date,Gross Sales\n2026-10-01,$20.00\n2026-10-30,$40.00\n")
    assert r["metrics"]["avg_ticket"] == 30 and r["metrics"]["monthly_revenue"] > 0
