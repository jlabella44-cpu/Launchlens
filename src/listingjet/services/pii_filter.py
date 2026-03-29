"""
PII filter for AI prompts.

Strips personally identifiable fields before sending listing data
to external AI providers (OpenAI, Claude, Google Vision).
"""

PII_FIELDS = {
    "agent_name",
    "agent_email",
    "agent_phone",
    "owner_name",
    "seller_name",
    "buyer_name",
    "contact_name",
    "contact_email",
    "contact_phone",
    "phone",
    "email",
    "ssn",
}


def sanitize_for_prompt(data: dict) -> dict:
    """Remove PII fields from a dict before sending to an external AI provider."""
    if not isinstance(data, dict):
        return data
    return {k: sanitize_for_prompt(v) if isinstance(v, dict) else v for k, v in data.items() if k not in PII_FIELDS}
