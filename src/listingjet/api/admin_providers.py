"""
Admin endpoints for LLM/vision provider configuration and cost transparency.

Exposes the active routing configuration plus the per-token rate card so
operators can verify which provider each agent/tenant is using and forecast
costs.
"""
from fastapi import APIRouter, Depends

from listingjet.api.deps import require_superadmin
from listingjet.config import settings
from listingjet.models.user import User
from listingjet.providers._routing import (
    _agent_routing,
    _tenant_routing,
    resolve_llm_provider,
    resolve_vision_provider,
)
from listingjet.services.metrics import PROVIDER_COSTS, TOKEN_COSTS

router = APIRouter()

_KNOWN_LLM_AGENTS = ("content", "social_content", "cma_report")
_KNOWN_VISION_AGENTS = ("vision", "floorplan", "chapter")


@router.get("/providers/config")
async def providers_config(user: User = Depends(require_superadmin)) -> dict:
    """Return the active provider routing configuration."""
    resolved_llm = {
        agent: resolve_llm_provider(agent) for agent in _KNOWN_LLM_AGENTS
    }
    resolved_vision = {
        agent: resolve_vision_provider(agent, default=settings.vision_provider_tier1)
        for agent in _KNOWN_VISION_AGENTS
    }
    return {
        "global": {
            "llm_provider": settings.llm_provider,
            "vision_provider_tier1": settings.vision_provider_tier1,
            "vision_provider_tier2": settings.vision_provider_tier2,
            "llm_fallback_enabled": settings.llm_fallback_enabled,
            "qwen_enable_cache": settings.qwen_enable_cache,
            "gemma_base_url": settings.gemma_base_url or None,
            "gemma_model": settings.gemma_model,
        },
        "per_agent_overrides": _agent_routing(),
        "tenant_override_count": len(_tenant_routing()),
        "resolved": {"llm": resolved_llm, "vision": resolved_vision},
    }


@router.get("/providers/rate-card")
async def providers_rate_card(user: User = Depends(require_superadmin)) -> dict:
    """Return per-1M-token and per-call cost estimates used for metrics."""
    return {
        "per_1m_tokens_usd": {
            name: {"input": rates[0], "output": rates[1]}
            for name, rates in TOKEN_COSTS.items()
        },
        "per_call_usd": dict(PROVIDER_COSTS),
    }


@router.post("/providers/estimate")
async def estimate_cost(
    provider: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    call_count: int = 0,
    user: User = Depends(require_superadmin),
) -> dict:
    """Estimate cost for a hypothetical workload."""
    token_cost = 0.0
    if provider in TOKEN_COSTS:
        in_rate, out_rate = TOKEN_COSTS[provider]
        token_cost = (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
    call_cost = PROVIDER_COSTS.get(provider, 0.0) * call_count
    return {
        "provider": provider,
        "token_cost_usd": round(token_cost, 6),
        "call_cost_usd": round(call_cost, 6),
        "total_usd": round(token_cost + call_cost, 6),
    }
