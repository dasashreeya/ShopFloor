from datetime import datetime
from typing import Protocol

from shopfloor.models import ConnectorKind, Event


class Connector(Protocol):
    """Every integration (Square, Toast, QuickBooks, Gmail, phone, GBP) normalizes into Events.

    Real implementations go in this package (e.g. square.py using Square's Orders API);
    `scopes` is what the platform requests and what `fire` revokes.
    """

    kind: ConnectorKind
    scopes: list[str]

    def fetch(self, since: datetime, until: datetime) -> list[Event]: ...


SCOPES: dict[ConnectorKind, list[str]] = {
    ConnectorKind.SQUARE: ["ORDERS_READ", "PAYMENTS_READ", "CUSTOMERS_READ"],
    ConnectorKind.TOAST: ["orders:read", "guests:read"],
    ConnectorKind.QUICKBOOKS: ["com.intuit.quickbooks.accounting"],
    ConnectorKind.GMAIL: ["gmail.readonly"],
    ConnectorKind.PHONE: ["call_logs:read", "sms:send"],
    ConnectorKind.GOOGLE_BUSINESS: ["business.manage"],
}
