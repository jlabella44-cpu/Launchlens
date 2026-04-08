"""
MLS Publish API — one-click publish to MLS via RESO Web API,
plus CRUD for tenant MLS connections.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user
from listingjet.api.schemas.mls_publish import (
    ConnectionTestResult,
    CreateMLSConnectionRequest,
    MLSConnectionResponse,
    PublishRequest,
    PublishResponse,
    PublishStatusResponse,
    UpdateMLSConnectionRequest,
)
from listingjet.database import get_db
from listingjet.models.listing import Listing, ListingState
from listingjet.models.mls_connection import MLSConnection
from listingjet.models.mls_publish_record import MLSPublishRecord, PublishStatus
from listingjet.models.user import User
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.events import emit_event
from listingjet.services.reso_adapter import RESOAdapter, RESOConnectionConfig
from listingjet.temporal_client import get_temporal_client

logger = logging.getLogger(__name__)

router = APIRouter()

_PUBLISHABLE_STATES = {
    ListingState.APPROVED,
    ListingState.EXPORTING,
    ListingState.DELIVERED,
}

# ---------------------------------------------------------------------------
# One-click MLS Publish
# ---------------------------------------------------------------------------


@router.post("/{listing_id}/publish", response_model=PublishResponse)
async def publish_to_mls(
    listing_id: uuid.UUID,
    body: PublishRequest = PublishRequest(),
    _rl=Depends(rate_limit(5, 60)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a listing to the MLS via RESO Web API (one-click).

    Triggers the MLS Publish agent which submits the property record and
    photos to the configured MLS board.
    """
    listing = (
        await db.execute(
            select(Listing).where(
                Listing.id == listing_id,
                Listing.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.state not in _PUBLISHABLE_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot publish: listing is {listing.state.value}. Must be approved/delivered first.",
        )

    # Resolve MLS connection
    if body.connection_id:
        conn = await db.get(MLSConnection, body.connection_id)
        if not conn or conn.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="MLS connection not found")
    else:
        result = await db.execute(
            select(MLSConnection)
            .where(
                MLSConnection.tenant_id == current_user.tenant_id,
                MLSConnection.is_active.is_(True),
            )
            .limit(1)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise HTTPException(
                status_code=400,
                detail="No active MLS connection configured. Set up a connection in Settings → MLS first.",
            )

    # Check for in-progress publish
    existing = (
        await db.execute(
            select(MLSPublishRecord).where(
                MLSPublishRecord.listing_id == listing_id,
                MLSPublishRecord.connection_id == conn.id,
                MLSPublishRecord.status.in_(
                    [
                        PublishStatus.PENDING,
                        PublishStatus.SUBMITTING_PROPERTY,
                        PublishStatus.SUBMITTING_MEDIA,
                    ]
                ),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A publish is already in progress for this listing.",
        )

    # Create publish record
    publish_record = MLSPublishRecord(
        tenant_id=current_user.tenant_id,
        listing_id=listing_id,
        connection_id=conn.id,
        status=PublishStatus.PENDING,
    )
    db.add(publish_record)
    listing.state = ListingState.PUBLISHING
    await db.commit()
    await db.refresh(publish_record)

    # Trigger the publish agent via Temporal
    from listingjet.agents.base import AgentContext

    try:
        client = get_temporal_client()
        await client.execute_activity_direct(
            "run_mls_publish",
            AgentContext(listing_id=str(listing_id), tenant_id=str(current_user.tenant_id)),
        )
    except Exception:
        # Fallback: run the agent directly if Temporal is unavailable
        logger.warning("Temporal unavailable for MLS publish — running inline")
        from listingjet.agents.mls_publish import MLSPublishAgent

        try:
            ctx = AgentContext(
                listing_id=str(listing_id),
                tenant_id=str(current_user.tenant_id),
            )
            await MLSPublishAgent().instrumented_execute(ctx)
        except Exception as agent_exc:
            logger.exception("MLS publish agent failed for listing %s", listing_id)
            # Update record status
            publish_record.status = PublishStatus.FAILED
            publish_record.error_message = str(agent_exc)[:2000]
            listing.state = ListingState.DELIVERED
            await db.commit()
            raise HTTPException(
                status_code=502,
                detail=f"MLS publish failed: {str(agent_exc)[:200]}",
            )

    await emit_event(
        session=db,
        event_type="mls_publish.initiated",
        payload={
            "connection_id": str(conn.id),
            "mls_board": conn.mls_board,
        },
        tenant_id=str(current_user.tenant_id),
        listing_id=str(listing_id),
    )
    await db.commit()

    return PublishResponse(
        publish_record_id=publish_record.id,
        listing_id=listing_id,
        status="publishing",
        message=f"Publishing to {conn.mls_board} via RESO Web API",
    )


@router.get("/{listing_id}/publish-status", response_model=list[PublishStatusResponse])
async def get_publish_status(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all MLS publish attempts for a listing."""
    listing = (
        await db.execute(
            select(Listing).where(
                Listing.id == listing_id,
                Listing.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    result = await db.execute(
        select(MLSPublishRecord, MLSConnection.name)
        .join(MLSConnection, MLSPublishRecord.connection_id == MLSConnection.id)
        .where(MLSPublishRecord.listing_id == listing_id)
        .order_by(MLSPublishRecord.created_at.desc())
    )
    rows = result.all()

    return [
        PublishStatusResponse(
            id=record.id,
            listing_id=record.listing_id,
            connection_id=record.connection_id,
            connection_name=conn_name,
            status=record.status.value,
            reso_listing_key=record.reso_listing_key,
            reso_property_id=record.reso_property_id,
            photos_submitted=record.photos_submitted,
            photos_accepted=record.photos_accepted,
            error_message=record.error_message,
            error_code=record.error_code,
            retry_count=record.retry_count,
            submitted_at=record.submitted_at,
            confirmed_at=record.confirmed_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record, conn_name in rows
    ]


# ---------------------------------------------------------------------------
# MLS Connections CRUD
# ---------------------------------------------------------------------------

connections_router = APIRouter()


@connections_router.get("", response_model=list[MLSConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all MLS connections for the tenant."""
    result = await db.execute(
        select(MLSConnection)
        .where(MLSConnection.tenant_id == current_user.tenant_id)
        .order_by(MLSConnection.created_at.desc())
    )
    return [MLSConnectionResponse.model_validate(c) for c in result.scalars().all()]


@connections_router.post("", response_model=MLSConnectionResponse, status_code=201)
async def create_connection(
    body: CreateMLSConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new MLS connection for the tenant."""
    conn = MLSConnection(
        tenant_id=current_user.tenant_id,
        name=body.name,
        mls_board=body.mls_board,
        reso_api_url=body.reso_api_url,
        oauth_token_url=body.oauth_token_url,
        client_id=body.client_id,
        client_secret_encrypted=body.client_secret,  # TODO: encrypt at rest
        bearer_token_encrypted=body.bearer_token,
        config=body.config,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return MLSConnectionResponse.model_validate(conn)


@connections_router.get("/{connection_id}", response_model=MLSConnectionResponse)
async def get_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific MLS connection."""
    conn = await db.get(MLSConnection, connection_id)
    if not conn or conn.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="MLS connection not found")
    return MLSConnectionResponse.model_validate(conn)


@connections_router.patch("/{connection_id}", response_model=MLSConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    body: UpdateMLSConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing MLS connection."""
    conn = await db.get(MLSConnection, connection_id)
    if not conn or conn.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    update_data = body.model_dump(exclude_unset=True)
    # Map client_secret → encrypted field
    if "client_secret" in update_data:
        update_data["client_secret_encrypted"] = update_data.pop("client_secret")
    if "bearer_token" in update_data:
        update_data["bearer_token_encrypted"] = update_data.pop("bearer_token")

    for key, value in update_data.items():
        setattr(conn, key, value)

    await db.commit()
    await db.refresh(conn)
    return MLSConnectionResponse.model_validate(conn)


@connections_router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an MLS connection."""
    conn = await db.get(MLSConnection, connection_id)
    if not conn or conn.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    # Check for in-progress publishes using this connection
    active_publishes = (
        (
            await db.execute(
                select(MLSPublishRecord).where(
                    MLSPublishRecord.connection_id == connection_id,
                    MLSPublishRecord.status.in_(
                        [
                            PublishStatus.PENDING,
                            PublishStatus.SUBMITTING_PROPERTY,
                            PublishStatus.SUBMITTING_MEDIA,
                        ]
                    ),
                )
            )
        )
        .scalars()
        .first()
    )
    if active_publishes:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: active publishes are using this connection.",
        )

    await db.delete(conn)
    await db.commit()


@connections_router.post("/{connection_id}/test", response_model=ConnectionTestResult)
async def test_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test an MLS connection by hitting the RESO metadata endpoint."""
    conn = await db.get(MLSConnection, connection_id)
    if not conn or conn.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="MLS connection not found")

    adapter = RESOAdapter(
        config=RESOConnectionConfig(
            base_url=conn.reso_api_url,
            oauth_token_url=conn.oauth_token_url,
            client_id=conn.client_id,
            client_secret=conn.client_secret_encrypted,
            bearer_token=conn.bearer_token_encrypted,
        )
    )

    result = await adapter.test_connection()
    now = datetime.now(timezone.utc)

    conn.last_tested_at = now
    conn.last_test_status = result["status"]
    await db.commit()

    return ConnectionTestResult(
        connection_id=conn.id,
        status=result["status"],
        error=result.get("error"),
        tested_at=now,
    )
