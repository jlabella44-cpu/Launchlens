"""Read-only tool functions for the AI help agent.

Each function takes a db session and tenant_id (injected server-side from the
authenticated user -- NEVER from the LLM) and returns a JSON-serialisable dict.
All queries are scoped to the tenant via WHERE clauses.
"""
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.config.tiers import CREDIT_BUNDLES, TIER_DEFAULTS, get_bundles_for_tier
from listingjet.models.addon_catalog import AddonCatalog
from listingjet.models.addon_purchase import AddonPurchase
from listingjet.models.listing import Listing, ListingState
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.credits import CreditService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Anthropic tool definitions (sent to Claude)
# NOTE: tenant_id is intentionally absent -- it's injected server-side.
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_listings_summary",
        "description": (
            "Get a summary of the user's listings grouped by status. "
            "Optionally filter by a specific listing state. "
            "Returns counts per state and the most recent listings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state_filter": {
                    "type": "string",
                    "description": (
                        "Optional filter by listing state. One of: new, uploading, "
                        "analyzing, awaiting_review, in_review, approved, delivered, "
                        "pipeline_timeout, failed, cancelled, exporting, demo"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of recent listings to return (default 10, max 25).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_listing_detail",
        "description": "Get full details for a single listing by its ID, including address, state, timestamps, and credit cost.",
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {
                    "type": "string",
                    "description": "The UUID of the listing to look up.",
                },
            },
            "required": ["listing_id"],
        },
    },
    {
        "name": "search_listings_by_address",
        "description": "Search for listings by address (partial match). Useful when the user mentions a street name or city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Address search term (street, city, etc.).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_credit_balance",
        "description": "Get the current credit balance, rollover balance, rollover cap, and billing period dates for the user's account.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_recent_transactions",
        "description": "Get recent credit transactions (debits, credits, refunds, grants, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of transactions to return (default 10, max 50).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_plan_info",
        "description": "Get the user's current subscription plan, tier, included monthly credits, per-listing cost, and rollover cap.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_credit_pricing",
        "description": "Get available credit bundle options with prices. Useful when a user asks about buying more credits.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_team_members",
        "description": "List all team members on the user's account with their names, emails, and roles.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_addon_catalog",
        "description": "List all available premium add-ons with their credit costs.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_listing_addons",
        "description": "Get add-ons purchased for a specific listing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "listing_id": {
                    "type": "string",
                    "description": "The UUID of the listing.",
                },
            },
            "required": ["listing_id"],
        },
    },
    {
        "name": "search_resolved_tickets",
        "description": (
            "Search previously resolved support tickets for similar issues. "
            "Use this BEFORE escalating to check if a similar problem was already solved. "
            "Returns matching tickets with their resolution notes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keywords describing the issue.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "request_human_support",
        "description": (
            "Escalate to human support by creating a support ticket. "
            "This creates a tracked ticket with the full chat transcript attached. "
            "Use this when the user is frustrated, asks the same question 3+ times, "
            "or when the issue requires human intervention. "
            "Always search_resolved_tickets first to check if a similar issue was already solved."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Brief summary of the user's issue for the support team.",
                },
            },
            "required": ["summary"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool function implementations
# ---------------------------------------------------------------------------

def _serialise_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _listing_to_dict(listing: Listing) -> dict:
    address = listing.address or {}
    address_str = address.get("formatted", "") or ", ".join(
        filter(None, [address.get("street"), address.get("city"), address.get("state"), address.get("zip")])
    )
    return {
        "id": str(listing.id),
        "address": address_str or "(no address)",
        "state": listing.state.value if listing.state else "unknown",
        "analysis_tier": listing.analysis_tier,
        "credit_cost": listing.credit_cost,
        "is_demo": listing.is_demo,
        "created_at": _serialise_datetime(listing.created_at),
        "updated_at": _serialise_datetime(listing.updated_at),
    }


async def get_listings_summary(
    db: AsyncSession, tenant_id: uuid.UUID, state_filter: str | None = None, limit: int = 10
) -> dict:
    limit = max(1, min(limit, 25))

    # Counts per state
    count_query = (
        select(Listing.state, func.count())
        .where(Listing.tenant_id == tenant_id)
        .group_by(Listing.state)
    )
    result = await db.execute(count_query)
    counts = {row[0].value: row[1] for row in result}

    # Recent listings
    listing_query = (
        select(Listing)
        .where(Listing.tenant_id == tenant_id)
        .order_by(Listing.created_at.desc())
        .limit(limit)
    )
    if state_filter:
        try:
            state_enum = ListingState(state_filter)
        except ValueError:
            return {"error": f"Invalid state '{state_filter}'. Valid states: {[s.value for s in ListingState]}"}
        listing_query = listing_query.where(Listing.state == state_enum)

    listings_result = await db.execute(listing_query)
    listings = [_listing_to_dict(row) for row in listings_result.scalars().all()]

    return {
        "total_listings": sum(counts.values()),
        "counts_by_state": counts,
        "recent_listings": listings,
    }


async def get_listing_detail(db: AsyncSession, tenant_id: uuid.UUID, listing_id: str) -> dict:
    try:
        lid = uuid.UUID(listing_id)
    except ValueError:
        return {"error": "Invalid listing ID format. Must be a UUID."}

    listing = (
        await db.execute(
            select(Listing).where(Listing.id == lid, Listing.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()

    if not listing:
        return {"error": "Listing not found. It may not exist or may belong to a different account."}

    return _listing_to_dict(listing)


async def search_listings_by_address(
    db: AsyncSession, tenant_id: uuid.UUID, query: str
) -> dict:
    query = query.strip()[:200]  # cap search length
    if len(query) < 2:
        return {"error": "Search query must be at least 2 characters."}

    # Search in the JSONB address field using cast-to-text ILIKE
    from sqlalchemy import String as SAString
    from sqlalchemy import cast
    result = await db.execute(
        select(Listing)
        .where(
            Listing.tenant_id == tenant_id,
            cast(Listing.address, SAString).ilike(f"%{query}%"),
        )
        .order_by(Listing.created_at.desc())
        .limit(10)
    )
    listings = [_listing_to_dict(row) for row in result.scalars().all()]
    return {"results": listings, "count": len(listings)}


async def get_credit_balance(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    svc = CreditService()
    try:
        balance = await svc.get_balance(db, tenant_id)
    except ValueError:
        return {"error": "No credit account found. Your account may not be fully set up yet."}
    return {
        "balance": balance.balance,
        "rollover_balance": balance.rollover_balance,
        "rollover_cap": balance.rollover_cap,
        "period_start": _serialise_datetime(balance.period_start),
        "period_end": _serialise_datetime(balance.period_end),
    }


async def get_recent_transactions(
    db: AsyncSession, tenant_id: uuid.UUID, limit: int = 10
) -> dict:
    limit = max(1, min(limit, 50))
    svc = CreditService()
    txns = await svc.get_transactions(db, tenant_id, limit=limit)
    return {
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "balance_after": t.balance_after,
                "type": t.transaction_type,
                "description": t.description or "",
                "created_at": _serialise_datetime(t.created_at),
            }
            for t in txns
        ]
    }


async def get_plan_info(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return {"error": "Tenant not found."}

    tier_info = TIER_DEFAULTS.get(tenant.plan, TIER_DEFAULTS.get(tenant.plan_tier, {}))

    return {
        "plan": tenant.plan,
        "plan_tier": tenant.plan_tier,
        "included_credits_per_month": tier_info.get("included_credits", 0),
        "rollover_cap": tier_info.get("rollover_cap", 0),
        "per_listing_credit_cost": tier_info.get("per_listing_credit_cost", 12),
        "billing_model": tenant.billing_model,
        "has_stripe_subscription": bool(tenant.stripe_subscription_id),
    }


async def get_credit_pricing(**kwargs) -> dict:
    # Return bundles for the free tier as a baseline reference
    bundles = get_bundles_for_tier("free")
    return {
        "bundles": [
            {
                "size": b["size"],
                "price": f"${b['price_cents'] / 100:.2f}",
                "per_credit": f"${b['per_credit_cents'] / 100:.2f}",
            }
            for b in bundles
        ],
        "note": "Credits can be purchased from the Billing page. Prices vary by tier.",
    }


async def get_team_members(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at)
    )
    users = result.scalars().all()
    return {
        "members": [
            {
                "name": u.name or "(no name)",
                "email": u.email,
                "role": u.role.value if u.role else "unknown",
                "joined": _serialise_datetime(u.created_at),
            }
            for u in users
        ],
        "count": len(users),
    }


async def get_addon_catalog(db: AsyncSession, **kwargs) -> dict:
    result = await db.execute(
        select(AddonCatalog).where(AddonCatalog.is_active.is_(True))
    )
    addons = result.scalars().all()
    return {
        "addons": [
            {
                "slug": a.slug,
                "name": a.name,
                "credit_cost": a.credit_cost,
            }
            for a in addons
        ]
    }


async def get_listing_addons(
    db: AsyncSession, tenant_id: uuid.UUID, listing_id: str
) -> dict:
    try:
        lid = uuid.UUID(listing_id)
    except ValueError:
        return {"error": "Invalid listing ID format."}

    result = await db.execute(
        select(AddonPurchase, AddonCatalog)
        .join(AddonCatalog, AddonPurchase.addon_id == AddonCatalog.id)
        .where(
            AddonPurchase.tenant_id == tenant_id,
            AddonPurchase.listing_id == lid,
        )
    )
    rows = result.all()
    return {
        "addons": [
            {
                "name": catalog.name,
                "slug": catalog.slug,
                "credit_cost": catalog.credit_cost,
                "status": purchase.status,
                "purchased_at": _serialise_datetime(purchase.created_at),
            }
            for purchase, catalog in rows
        ]
    }


async def search_resolved_tickets(
    db: AsyncSession, tenant_id: uuid.UUID, query: str
) -> dict:
    """Search resolved support tickets for similar issues."""
    from listingjet.models.support_ticket import SupportTicket, TicketStatus

    query = query.strip()[:200]
    if len(query) < 2:
        return {"results": [], "count": 0}

    from sqlalchemy import String as SAString
    from sqlalchemy import cast, or_

    result = await db.execute(
        select(SupportTicket)
        .where(
            SupportTicket.tenant_id == tenant_id,
            SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            or_(
                cast(SupportTicket.subject, SAString).ilike(f"%{query}%"),
                cast(SupportTicket.resolution_note, SAString).ilike(f"%{query}%"),
            ),
        )
        .order_by(SupportTicket.updated_at.desc())
        .limit(3)
    )
    tickets = result.scalars().all()
    return {
        "results": [
            {
                "id": str(t.id),
                "subject": t.subject,
                "resolution": t.resolution_note or "(no resolution note)",
                "resolved_at": _serialise_datetime(t.updated_at),
            }
            for t in tickets
        ],
        "count": len(tickets),
    }


async def request_human_support(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    summary: str,
    user_email: str,
    user_name: str,
    session_id: str = "",
) -> dict:
    """Create a support ticket with the chat transcript attached."""
    from listingjet.models.support_ticket import (
        SupportMessage,
        SupportTicket,
        TicketCategory,
        TicketPriority,
        TicketStatus,
    )

    # Look up user ID
    user_result = await db.execute(
        select(User).where(User.email == user_email, User.tenant_id == tenant_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return {"status": "failed", "message": "Could not find your account. Please email support@listingjet.com directly."}

    # Load chat transcript from Redis
    chat_transcript = None
    if session_id:
        try:
            from listingjet.services.help_agent import _load_history
            chat_transcript = _load_history(user.id, session_id)
        except Exception:
            pass

    try:
        ticket = SupportTicket(
            tenant_id=tenant_id,
            user_id=user.id,
            subject=f"AI Agent Escalation: {summary[:80]}",
            category=TicketCategory.OTHER,
            priority=TicketPriority.NORMAL,
            status=TicketStatus.OPEN,
            chat_session_id=session_id or None,
        )
        db.add(ticket)
        await db.flush()

        metadata = {}
        if chat_transcript:
            metadata["chat_transcript"] = chat_transcript

        message = SupportMessage(
            ticket_id=ticket.id,
            user_id=user.id,
            content=summary,
            is_admin_reply=False,
            metadata_=metadata if metadata else None,
        )
        db.add(message)

        # Also send email notification
        from listingjet.services.email import get_email_service
        email_svc = get_email_service()
        email_svc.send(
            to="support@listingjet.com",
            subject=f"Help Agent Escalation — {user_name or user_email}",
            html_body=(
                f"<h3>Support Ticket Created via AI Help Agent</h3>"
                f"<p><strong>Ticket ID:</strong> {ticket.id}</p>"
                f"<p><strong>User:</strong> {user_name} ({user_email})</p>"
                f"<p><strong>Summary:</strong></p>"
                f"<p>{summary}</p>"
            ),
        )

        ticket_short = str(ticket.id)[:8]
        return {
            "status": "created",
            "ticket_id": str(ticket.id),
            "message": f"I've created support ticket #{ticket_short} for you. Our team will respond shortly. You can track it on the Support page.",
        }
    except Exception:
        logger.exception("help_agent.ticket_creation_failed tenant=%s", tenant_id)
        return {"status": "failed", "message": "We couldn't create the support ticket right now. Please try again or email support@listingjet.com directly."}


# ---------------------------------------------------------------------------
# Tool dispatcher -- maps tool name to function, enforcing tenant scope
# ---------------------------------------------------------------------------

# Tools that don't need db/tenant (static data)
_STATIC_TOOLS = {"get_credit_pricing", "get_addon_catalog"}

# Tools that need tenant but don't need extra user info
_TENANT_TOOLS = {
    "get_listings_summary": get_listings_summary,
    "get_listing_detail": get_listing_detail,
    "search_listings_by_address": search_listings_by_address,
    "get_credit_balance": get_credit_balance,
    "get_recent_transactions": get_recent_transactions,
    "get_plan_info": get_plan_info,
    "get_team_members": get_team_members,
    "get_listing_addons": get_listing_addons,
}


async def execute_tool(
    tool_name: str,
    tool_input: dict,
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_email: str = "",
    user_name: str = "",
    session_id: str = "",
) -> str:
    """Execute a tool by name and return JSON string result.

    tenant_id is always injected from the authenticated session.
    """
    try:
        if tool_name == "get_credit_pricing":
            result = await get_credit_pricing()
        elif tool_name == "get_addon_catalog":
            result = await get_addon_catalog(db)
        elif tool_name == "search_resolved_tickets":
            result = await search_resolved_tickets(
                db, tenant_id,
                query=str(tool_input.get("query", ""))[:200],
            )
        elif tool_name == "request_human_support":
            result = await request_human_support(
                db, tenant_id,
                summary=str(tool_input.get("summary", ""))[:1000],
                user_email=user_email,
                user_name=user_name,
                session_id=session_id,
            )
        elif tool_name in _TENANT_TOOLS:
            fn = _TENANT_TOOLS[tool_name]
            # Filter tool_input to only expected params (drop tenant_id if LLM tries)
            safe_input = {k: v for k, v in tool_input.items() if k != "tenant_id"}
            result = await fn(db=db, tenant_id=tenant_id, **safe_input)
        else:
            result = {"error": f"Unknown tool '{tool_name}'."}
    except Exception:
        logger.exception("help_agent.tool_error tool=%s tenant=%s", tool_name, tenant_id)
        result = {"error": "An internal error occurred while looking up this information."}

    return json.dumps(result, default=str)
