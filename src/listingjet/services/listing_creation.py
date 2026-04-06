"""Listing creation service — encapsulates billing, quota, and persistence logic."""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.services.credits import CreditService
from listingjet.services.plan_limits import check_listing_quota

logger = logging.getLogger(__name__)


class ListingQuotaExceededError(Exception):
    def __init__(self, current_count: int):
        self.current_count = current_count
        super().__init__(f"Monthly listing limit reached ({current_count})")


class ListingCreationService:
    """Handles all business logic for creating a new listing:
    credit deduction (credit-billed tenants), monthly quota checks
    (legacy tenants), and persistence.
    """

    def __init__(self, credit_svc: CreditService | None = None):
        self._credit_svc = credit_svc or CreditService()

    async def create(
        self,
        session: AsyncSession,
        tenant: Tenant,
        tenant_id: uuid.UUID,
        address: dict,
        metadata: dict,
        idempotency_key: str | None = None,
    ) -> Listing:
        """Create a listing, handling billing and quota enforcement.

        Args:
            session: DB session (caller manages commit/rollback).
            tenant: The resolved Tenant object.
            tenant_id: Tenant UUID.
            address: Address dict (validated by caller).
            metadata: Metadata dict (validated by caller).
            idempotency_key: Optional client-provided key to prevent duplicates.

        Returns:
            The new Listing object (flushed but not committed).

        Raises:
            InsufficientCreditsError: Not enough credits for credit-billed tenant.
            ListingQuotaExceededError: Monthly quota exceeded for legacy tenant.
            ValueError: Duplicate idempotency key.
        """
        # Idempotency: check for existing listing with same key
        if idempotency_key:
            existing = (await session.execute(
                select(Listing).where(
                    Listing.tenant_id == tenant_id,
                    Listing.metadata_["idempotency_key"].astext == idempotency_key,
                ).limit(1)
            )).scalar_one_or_none()
            if existing:
                return existing

        listing_id = uuid.uuid4()
        listing = Listing(
            id=listing_id,
            tenant_id=tenant_id,
            address=address,
            metadata_={**metadata, **({"idempotency_key": idempotency_key} if idempotency_key else {})},
            state=ListingState.DRAFT if tenant.billing_model == "credit" else ListingState.NEW,
        )

        if tenant.billing_model != "credit":
            # Legacy billing: monthly quota check (credits deferred to start-pipeline for credit users)
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            count_result = await session.execute(
                select(func.count(Listing.id)).where(
                    Listing.tenant_id == tenant_id,
                    Listing.created_at >= month_start,
                )
            )
            current_count = count_result.scalar() or 0
            if not check_listing_quota(tenant.plan, current_count):
                raise ListingQuotaExceededError(current_count)

        session.add(listing)
        await session.flush()
        return listing
