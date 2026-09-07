"""Feature flags. FEATURES is a comma-separated list in the environment.

Deferred features (learning, health score, performance intelligence, help
agent, microsite, webhooks, listing permissions) are off unless listed.
"""
from fastapi import HTTPException

from listingjet.config import settings

FLAG_NAMES = frozenset({
    "learning", "health_score", "performance_intelligence", "help_agent",
    "microsite", "webhooks", "listing_permissions",
})


def enabled_set() -> set[str]:
    raw = settings.features or ""
    names = {n.strip() for n in raw.split(",") if n.strip()}
    unknown = names - FLAG_NAMES
    if unknown:
        raise ValueError(f"unknown feature(s) in FEATURES: {sorted(unknown)}")
    return names


def enabled(name: str) -> bool:
    if name not in FLAG_NAMES:
        raise ValueError(f"unknown feature {name!r}")
    return name in enabled_set()


def require_feature(name: str):
    if name not in FLAG_NAMES:
        raise ValueError(f"unknown feature {name!r}")

    async def _dep() -> None:
        if not enabled(name):
            raise HTTPException(status_code=404, detail="Feature not enabled")

    return _dep
