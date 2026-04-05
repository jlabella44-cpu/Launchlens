# src/listingjet/providers/_routing.py
"""
Per-agent provider routing.

Reads settings.agent_model_routing (a JSON string parsed to a dict) to let
each agent pick its own LLM/vision provider. Falls back to the global
LLM_PROVIDER / VISION_PROVIDER_TIER1 values when an agent isn't listed.

Example AGENT_MODEL_ROUTING env var:
    {"llm": {"floorplan": "qwen", "social_content": "gemma"},
     "vision": {"photo_compliance": "gemma"}}
"""
import json
import logging

from listingjet.config import settings

logger = logging.getLogger(__name__)


def _parse_routing() -> dict:
    raw = settings.agent_model_routing
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data
    except json.JSONDecodeError:
        logger.warning("AGENT_MODEL_ROUTING is not valid JSON, ignoring")
        return {}


def resolve_llm_provider(agent: str | None) -> str:
    """Return the LLM provider name for *agent* (e.g. 'qwen', 'claude')."""
    if agent:
        routing = _parse_routing().get("llm", {})
        if agent in routing:
            return routing[agent]
    return settings.llm_provider


def resolve_vision_provider(agent: str | None, default: str) -> str:
    """Return the vision provider name for *agent*."""
    if agent:
        routing = _parse_routing().get("vision", {})
        if agent in routing:
            return routing[agent]
    return default
