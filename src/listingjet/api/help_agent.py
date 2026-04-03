"""AI help agent API — chat, history, feedback, and admin stats."""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from listingjet.api.deps import get_current_user, require_admin
from listingjet.api.schemas.help_agent import (
    AdminHelpAgentStatsResponse,
    ChatHistoryResponse,
    ChatMessage,
    ChatMessageRequest,
    FeedbackRequest,
    FeedbackResponse,
)
from listingjet.database import get_db
from listingjet.models.tenant import Tenant
from listingjet.models.user import User
from listingjet.services.endpoint_rate_limit import rate_limit
from listingjet.services.help_agent import (
    HelpAgentService,
    clear_history,
    get_history,
    save_feedback,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=Depends(rate_limit(20, 60)),
):
    """Send a message to the AI help agent. Returns an SSE stream."""
    session_id = body.session_id or str(uuid.uuid4())

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    service = HelpAgentService()

    async def event_stream():
        # Send session ID as first event
        yield f'data: {json.dumps({"type": "session", "session_id": session_id})}\n\n'

        async for chunk in service.chat(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            tenant_plan=tenant.plan,
            user_email=current_user.email,
            user_name=current_user.name or "",
            message=body.message,
            session_id=session_id,
            db=db,
        ):
            yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve conversation history for a session."""
    messages = get_history(current_user.id, session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatMessage(role=m["role"], content=m["content"])
            for m in messages
            if m.get("role") in ("user", "assistant")
        ],
    )


@router.delete("/history")
async def delete_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Clear conversation history for a session."""
    clear_history(current_user.id, session_id)
    return {"status": "cleared"}


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    body: FeedbackRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit thumbs up/down feedback for a help agent response."""
    save_feedback(current_user.id, body.session_id, body.message_index, body.rating)
    return FeedbackResponse(status="recorded")


@router.get("/admin/stats", response_model=AdminHelpAgentStatsResponse)
async def get_admin_stats(
    date: str | None = None,
    current_user: User = Depends(require_admin),
):
    """Get help agent usage statistics (admin only)."""
    import redis as redis_lib

    from listingjet.config import settings

    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)

        # Message counts by tenant
        msg_key = f"help:stats:messages:{target_date}"
        messages_raw = r.hgetall(msg_key)
        messages_by_tenant = {k.decode(): int(v) for k, v in messages_raw.items()}

        # Tool usage
        tool_key = f"help:stats:tools:{target_date}"
        tools_raw = r.hgetall(tool_key)
        tool_usage = {k.decode(): int(v) for k, v in tools_raw.items()}

        # Feedback summary
        feedback_key = f"help:feedback:{target_date}"
        feedback_entries = r.lrange(feedback_key, 0, -1)
        up_count = 0
        down_count = 0
        for entry in feedback_entries:
            data = json.loads(entry)
            if data.get("rating") == "up":
                up_count += 1
            else:
                down_count += 1

        return AdminHelpAgentStatsResponse(
            date=target_date,
            total_messages=sum(messages_by_tenant.values()),
            messages_by_tenant=messages_by_tenant,
            tool_usage=tool_usage,
            feedback_summary={"up": up_count, "down": down_count},
        )
    except Exception:
        logger.exception("help_agent.admin_stats_error")
        raise HTTPException(503, "Unable to retrieve stats — Redis may be unavailable")
