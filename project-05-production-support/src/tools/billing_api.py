from langchain_core.tools import tool

_MOCK_INVOICES = {
    "INV-001": {"id": "INV-001", "amount": 99.00, "status": "paid", "date": "2024-01-15"},
    "INV-002": {"id": "INV-002", "amount": 49.00, "status": "overdue", "date": "2024-02-01"},
    "INV-003": {"id": "INV-003", "amount": 199.00, "status": "paid", "date": "2024-03-10"},
}

_MOCK_SUBSCRIPTIONS = {
    "user_001": {"tier": "pro", "status": "active", "renewal_date": "2024-07-01"},
    "user_002": {"tier": "free", "status": "active", "renewal_date": None},
    "user_003": {"tier": "enterprise", "status": "active", "renewal_date": "2025-01-01"},
}


@tool
def lookup_invoice(invoice_id: str) -> dict:
    """Look up an invoice by ID. Returns invoice details including amount, status, and date."""
    return _MOCK_INVOICES.get(invoice_id, {"error": f"Invoice {invoice_id} not found"})


@tool
def process_refund(invoice_id: str, reason: str) -> dict:
    """Initiate a refund for a given invoice. Requires invoice ID and reason."""
    if invoice_id not in _MOCK_INVOICES:
        return {"error": f"Invoice {invoice_id} not found"}
    return {
        "status": "approved",
        "invoice_id": invoice_id,
        "message": f"Refund initiated. Reason: {reason}. Allow 3-5 business days.",
    }


@tool
def get_subscription_status(user_id: str) -> dict:
    """Retrieve the subscription tier and status for a given user ID."""
    return _MOCK_SUBSCRIPTIONS.get(
        user_id,
        {"tier": "free", "status": "active", "renewal_date": None},
    )


billing_tools = [lookup_invoice, process_refund, get_subscription_status]
