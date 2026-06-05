from langchain_core.tools import tool

_DOCS: dict[str, str] = {
    "authentication": (
        "Authenticate using your API key as a Bearer token in the Authorization header. "
        "Keys are generated in Dashboard > Settings > API Keys."
    ),
    "rate_limits": (
        "Free: 100 req/day. Pro: 10,000 req/day. Enterprise: unlimited. "
        "Rate limit headers (X-RateLimit-Remaining, X-RateLimit-Reset) are included in every response."
    ),
    "webhooks": (
        "Configure webhooks under Settings > Integrations. We POST JSON payloads with HMAC-SHA256 "
        "signatures in the X-Signature header. Retry policy: 3 attempts with exponential backoff."
    ),
    "exports": (
        "Data exports are available in CSV and JSON from Settings > Data > Export. "
        "Exports are async; a download link is emailed when ready."
    ),
    "integrations": (
        "Native integrations: Slack, Jira, GitHub, Zapier. "
        "All integrations are configured via OAuth in Settings > Integrations."
    ),
    "two_factor": (
        "Two-factor authentication can be enabled under Account > Security. "
        "Supported methods: TOTP (Google Authenticator) and SMS."
    ),
    "billing": (
        "Billing is managed under Settings > Billing. "
        "We accept Visa, Mastercard, and AMEX. Invoices are emailed monthly."
    ),
}


@tool
def search_documentation(query: str) -> str:
    """Search product documentation for technical information about features, configuration, and integrations."""
    q = query.lower()
    hits = [content for topic, content in _DOCS.items() if topic in q or any(w in q for w in topic.split("_"))]
    if not hits:
        return "No documentation found for that query. Please try different terms or contact support."
    return "\n\n".join(hits)


technical_tools = [search_documentation]
