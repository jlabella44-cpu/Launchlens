"""
AI consent enforcement helpers.

Defense-in-depth: the `/listings/{id}/start-pipeline` endpoint already checks
the caller's `ai_consent_at` before enqueueing a workflow. These helpers are
for agents that run later inside the workflow — if consent is revoked while
the pipeline is in flight, agents calling third-party AI providers should
halt before sending any data.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.user import User

logger = logging.getLogger(__name__)


class ConsentRevokedError(RuntimeError):
    """Raised when no consenting user remains for a tenant mid-pipeline."""


async def tenant_has_ai_consent(session: AsyncSession, tenant_id: uuid.UUID | str) -> bool:
    """Return True if any user in the tenant has granted AI processing consent."""
    if isinstance(tenant_id, str):
        tenant_id = uuid.UUID(tenant_id)
    result = await session.execute(
        select(User.id)
        .where(User.tenant_id == tenant_id, User.ai_consent_at.isnot(None))
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def require_tenant_ai_consent(
    session: AsyncSession,
    tenant_id: uuid.UUID | str,
    *,
    agent_name: str,
) -> None:
    """Raise ConsentRevokedError if no user in the tenant has AI consent.

    Agents that send data to third-party AI providers should call this at the
    top of execute() so revocations mid-pipeline halt the workflow before any
    PII leaves the system.
    """
    if not await tenant_has_ai_consent(session, tenant_id):
        logger.warning(
            "ai_consent.revoked agent=%s tenant=%s — halting",
            agent_name,
            tenant_id,
        )
        raise ConsentRevokedError(
            f"{agent_name} halted: no user in tenant has AI processing consent"
        )
