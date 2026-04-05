# src/listingjet/providers/_routing.py
"""
Per-agent and per-tenant provider routing.

Reads two JSON-string settings:

- AGENT_MODEL_ROUTING: global per-agent overrides, e.g.
      {"llm": {"floorplan": "qwen"},
       "vision": {"photo_compliance": "gemma"}}
- TENANT_MODEL_ROUTING: per-tenant overrides (highest priority), e.g.
      {"<tenant_uuid>": {"llm": "claude",
                          "llm_per_agent": {"social_content": "gemma"},
                          "vision": "google"}}

Resolution order (first match wins):
    1. tenant-level per-agent override
    2. tenant-level provider default
    3. global per-agent override
    4. global LLM_PROVIDER / VISION_PROVIDER_TIER1
"""
import json
import logging

from listingjet.config import settings

logger = logging.getLogger(__name__)


def _parse(raw: str, label: str) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data
    except json.JSONDecodeError:
        logger.warning("%s is not valid JSON, ignoring", label)
        return {}


def _agent_routing() -> dict:
    return _parse(settings.agent_model_routing, "AGENT_MODEL_ROUTING")


def _tenant_routing() -> dict:
    return _parse(settings.tenant_model_routing, "TENANT_MODEL_ROUTING")


def _tenant_key(tenant_id) -> str | None:
    if tenant_id is None:
        return None
    return str(tenant_id)


def resolve_llm_provider(agent: str | None, tenant_id=None) -> str:
    """Return the LLM provider name for *agent* (e.g. 'qwen', 'claude')."""
    tkey = _tenant_key(tenant_id)
    if tkey:
        t = _tenant_routing().get(tkey, {})
        if agent and agent in t.get("llm_per_agent", {}):
            return t["llm_per_agent"][agent]
        if "llm" in t:
            return t["llm"]
    if agent:
        per_agent = _agent_routing().get("llm", {})
        if agent in per_agent:
            return per_agent[agent]
    return settings.llm_provider


def resolve_vision_provider(agent: str | None, default: str, tenant_id=None) -> str:
    """Return the vision provider name for *agent*."""
    tkey = _tenant_key(tenant_id)
    if tkey:
        t = _tenant_routing().get(tkey, {})
        if agent and agent in t.get("vision_per_agent", {}):
            return t["vision_per_agent"][agent]
        if "vision" in t:
            return t["vision"]
    if agent:
        per_agent = _agent_routing().get("vision", {})
        if agent in per_agent:
            return per_agent[agent]
    return default
