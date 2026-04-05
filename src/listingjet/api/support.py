"""Support ticket API — user-facing CRUD and admin management."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.api.deps import get_current_user, require_admin
from listingjet.api.schemas.support import (
    AdminTicketStatsResponse,
    AdminTicketUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
    TicketCreateRequest,
    TicketDetailResponse,
    TicketListResponse,
    TicketResponse,
)
from listingjet.database import get_db
from listingjet.models.support_ticket import (
    SupportMessage,
    SupportTicket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from listingjet.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ticket_to_response(ticket: SupportTicket, user: User | None = None) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        subject=ticket.subject,
        category=ticket.category.value if ticket.category else "other",
        priority=ticket.priority.value if ticket.priority else "normal",
        status=ticket.status.value if ticket.status else "open",
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        user_email=user.email if user else None,
        user_name=user.name if user else None,
        chat_session_id=ticket.chat_session_id,
        resolution_note=ticket.resolution_note,
    )


def _message_to_response(msg: SupportMessage, user: User | None = None) -> MessageResponse:
    transcript = None
    if msg.metadata_ and "chat_transcript" in msg.metadata_:
        transcript = msg.metadata_["chat_transcript"]
    return MessageResponse(
        id=msg.id,
        user_id=msg.user_id,
        content=msg.content,
        is_admin_reply=msg.is_admin_reply,
        created_at=msg.created_at,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        chat_transcript=transcript,
    )


async def _load_users_map(db: AsyncSession, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    body: TicketCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new support ticket."""
    try:
        category = TicketCategory(body.category)
    except ValueError:
        raise HTTPException(400, f"Invalid category. Must be one of: {[c.value for c in TicketCategory]}")
    try:
        priority = TicketPriority(body.priority)
    except ValueError:
        raise HTTPException(400, f"Invalid priority. Must be one of: {[p.value for p in TicketPriority]}")

    ticket = SupportTicket(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        subject=body.subject,
        category=category,
        priority=priority,
        status=TicketStatus.OPEN,
    )
    db.add(ticket)
    await db.flush()

    message = SupportMessage(
        ticket_id=ticket.id,
        user_id=current_user.id,
        content=body.description,
        is_admin_reply=False,
    )
    db.add(message)

    # Send notification email (fire-and-forget)
    try:
        from listingjet.services.email import get_email_service
        email_svc = get_email_service()
        email_svc.send(
            to="support@listingjet.com",
            subject=f"New Support Ticket: {body.subject}",
            html_body=(
                f"<h3>New Support Ticket</h3>"
                f"<p><strong>From:</strong> {current_user.name or current_user.email} ({current_user.email})</p>"
                f"<p><strong>Category:</strong> {category.value} | <strong>Priority:</strong> {priority.value}</p>"
                f"<p><strong>Subject:</strong> {body.subject}</p>"
                f"<hr><p>{body.description}</p>"
            ),
        )
    except Exception:
        logger.exception("support_ticket_email_failed ticket=%s", ticket.id)

    await db.commit()
    await db.refresh(ticket)
    return _ticket_to_response(ticket, current_user)


@router.get("", response_model=TicketListResponse)
async def list_my_tickets(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's support tickets."""
    query = (
        select(SupportTicket)
        .where(
            SupportTicket.tenant_id == current_user.tenant_id,
            SupportTicket.user_id == current_user.id,
        )
        .order_by(SupportTicket.updated_at.desc())
    )
    if status:
        try:
            status_enum = TicketStatus(status)
            query = query.where(SupportTicket.status == status_enum)
        except ValueError:
            pass

    result = await db.execute(query)
    tickets = result.scalars().all()

    total = (await db.execute(
        select(func.count(SupportTicket.id)).where(
            SupportTicket.tenant_id == current_user.tenant_id,
            SupportTicket.user_id == current_user.id,
        )
    )).scalar() or 0

    return TicketListResponse(
        items=[_ticket_to_response(t, current_user) for t in tickets],
        total=total,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a ticket with its message thread."""
    ticket = (await db.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.tenant_id == current_user.tenant_id,
            SupportTicket.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    msgs_result = await db.execute(
        select(SupportMessage)
        .where(SupportMessage.ticket_id == ticket_id)
        .order_by(SupportMessage.created_at)
    )
    messages = msgs_result.scalars().all()

    user_ids = {m.user_id for m in messages}
    users_map = await _load_users_map(db, user_ids)

    return TicketDetailResponse(
        **_ticket_to_response(ticket, current_user).model_dump(),
        messages=[_message_to_response(m, users_map.get(m.user_id)) for m in messages],
    )


@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    ticket_id: uuid.UUID,
    body: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a reply to a ticket. Re-opens resolved tickets."""
    ticket = (await db.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.tenant_id == current_user.tenant_id,
            SupportTicket.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(409, "Cannot reply to a closed ticket")

    # Re-open resolved tickets when user replies
    if ticket.status == TicketStatus.RESOLVED:
        ticket.status = TicketStatus.OPEN

    message = SupportMessage(
        ticket_id=ticket_id,
        user_id=current_user.id,
        content=body.content,
        is_admin_reply=False,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return _message_to_response(message, current_user)


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.get("/admin/tickets", response_model=TicketListResponse)
async def admin_list_tickets(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all support tickets across tenants (admin only)."""
    query = select(SupportTicket).order_by(SupportTicket.updated_at.desc())
    count_query = select(func.count(SupportTicket.id))

    if status:
        try:
            status_enum = TicketStatus(status)
            query = query.where(SupportTicket.status == status_enum)
            count_query = count_query.where(SupportTicket.status == status_enum)
        except ValueError:
            pass
    if category:
        try:
            cat_enum = TicketCategory(category)
            query = query.where(SupportTicket.category == cat_enum)
            count_query = count_query.where(SupportTicket.category == cat_enum)
        except ValueError:
            pass
    if priority:
        try:
            pri_enum = TicketPriority(priority)
            query = query.where(SupportTicket.priority == pri_enum)
            count_query = count_query.where(SupportTicket.priority == pri_enum)
        except ValueError:
            pass

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    tickets = result.scalars().all()

    user_ids = {t.user_id for t in tickets}
    users_map = await _load_users_map(db, user_ids)

    return TicketListResponse(
        items=[_ticket_to_response(t, users_map.get(t.user_id)) for t in tickets],
        total=total,
    )


@router.get("/admin/tickets/stats", response_model=AdminTicketStatsResponse)
async def admin_ticket_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get support ticket statistics."""
    open_count = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == TicketStatus.OPEN)
    )).scalar() or 0

    in_progress_count = (await db.execute(
        select(func.count(SupportTicket.id)).where(SupportTicket.status == TicketStatus.IN_PROGRESS)
    )).scalar() or 0

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = (await db.execute(
        select(func.count(SupportTicket.id)).where(
            SupportTicket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            SupportTicket.updated_at >= today,
        )
    )).scalar() or 0

    # Average time to first admin reply (hours)
    avg_response = None
    try:
        sub = (
            select(
                SupportMessage.ticket_id,
                func.min(SupportMessage.created_at).label("first_reply"),
            )
            .where(SupportMessage.is_admin_reply.is_(True))
            .group_by(SupportMessage.ticket_id)
            .subquery()
        )
        avg_result = await db.execute(
            select(
                func.avg(
                    func.extract("epoch", sub.c.first_reply - SupportTicket.created_at) / 3600
                )
            ).join(sub, SupportTicket.id == sub.c.ticket_id)
        )
        val = avg_result.scalar()
        if val is not None:
            avg_response = round(float(val), 1)
    except Exception:
        logger.exception("support_stats_avg_response_failed")

    return AdminTicketStatsResponse(
        open_count=open_count,
        in_progress_count=in_progress_count,
        resolved_today=resolved_today,
        avg_response_hours=avg_response,
    )


@router.get("/admin/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def admin_get_ticket(
    ticket_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a ticket detail (admin — no tenant scoping)."""
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    msgs_result = await db.execute(
        select(SupportMessage)
        .where(SupportMessage.ticket_id == ticket_id)
        .order_by(SupportMessage.created_at)
    )
    messages = msgs_result.scalars().all()

    user_ids = {ticket.user_id} | {m.user_id for m in messages}
    users_map = await _load_users_map(db, user_ids)

    ticket_user = users_map.get(ticket.user_id)
    return TicketDetailResponse(
        **_ticket_to_response(ticket, ticket_user).model_dump(),
        messages=[_message_to_response(m, users_map.get(m.user_id)) for m in messages],
    )


@router.patch("/admin/tickets/{ticket_id}", response_model=TicketResponse)
async def admin_update_ticket(
    ticket_id: uuid.UUID,
    body: AdminTicketUpdateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update ticket status, assignment, or resolution note (admin only)."""
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    if body.status:
        try:
            ticket.status = TicketStatus(body.status)
        except ValueError:
            raise HTTPException(400, f"Invalid status. Must be one of: {[s.value for s in TicketStatus]}")

    if body.assigned_to is not None:
        ticket.assigned_to = uuid.UUID(body.assigned_to) if body.assigned_to else None

    if body.resolution_note is not None:
        ticket.resolution_note = body.resolution_note

    await db.commit()
    await db.refresh(ticket)

    user = await db.get(User, ticket.user_id)
    return _ticket_to_response(ticket, user)


@router.post("/admin/tickets/{ticket_id}/messages", response_model=MessageResponse, status_code=201)
async def admin_reply(
    ticket_id: uuid.UUID,
    body: MessageCreateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin reply to a ticket. Sends email notification to the ticket creator."""
    ticket = await db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    # Auto-set status to in_progress if currently open
    if ticket.status == TicketStatus.OPEN:
        ticket.status = TicketStatus.IN_PROGRESS

    message = SupportMessage(
        ticket_id=ticket_id,
        user_id=current_user.id,
        content=body.content,
        is_admin_reply=True,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Notify ticket creator via email (fire-and-forget)
    try:
        ticket_user = await db.get(User, ticket.user_id)
        if ticket_user:
            from listingjet.services.email import get_email_service
            email_svc = get_email_service()
            email_svc.send(
                to=ticket_user.email,
                subject=f"Re: {ticket.subject} — ListingJet Support",
                html_body=(
                    f"<p>Our team replied to your support ticket:</p>"
                    f"<hr><p>{body.content}</p><hr>"
                    f"<p><a href='https://app.listingjet.com/support'>View in ListingJet</a></p>"
                ),
            )
    except Exception:
        logger.exception("admin_reply_email_failed ticket=%s", ticket_id)

    return _message_to_response(message, current_user)
