import re
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass

from listingjet.services.metrics import StepTimer
from listingjet.telemetry import agent_span


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers that LLMs often add around JSON."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


@dataclass
class AgentContext:
    listing_id: str
    tenant_id: str


class BaseAgent(ABC):
    agent_name: str  # subclasses must define this class variable

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "agent_name") or "agent_name" not in cls.__dict__:
            raise TypeError(f"{cls.__name__} must define agent_name class variable")

    @abstractmethod
    async def execute(self, context: AgentContext): ...

    async def instrumented_execute(self, context: AgentContext) -> dict:
        """Wrap execute() with OpenTelemetry tracing and step metrics."""
        async with agent_span(self.agent_name, context.listing_id, context.tenant_id) as span:
            with StepTimer(self.agent_name):
                result = await self.execute(context)
                if span and isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, (int, float, bool, str)):
                            span.set_attribute(f"result.{key}", value)
                return result

    async def handle_failure(self, error: Exception, context: "AgentContext", session=None) -> None:
        """
        Emit a failure event and re-raise so Temporal retries the activity.
        session is optional — if None, failure is logged but not persisted.
        """
        if session is not None:
            from listingjet.services.events import emit_event
            await emit_event(
                session=session,
                event_type=f"{self.agent_name}.failed",
                payload={"error": str(error), "error_type": type(error).__name__},
                tenant_id=str(context.tenant_id),
                listing_id=str(context.listing_id) if context.listing_id else None,
            )

            # Send failure notification email
            if context.listing_id:
                try:
                    from listingjet.models.listing import Listing
                    from listingjet.services.notifications import notify_pipeline_failed
                    listing = await session.get(Listing, context.listing_id)
                    if listing:
                        await notify_pipeline_failed(
                            session, listing, str(context.tenant_id), str(error),
                        )
                except Exception:
                    pass  # Don't let notification failure mask the original error

        raise error  # Temporal sees the failure and applies retry policy

    @staticmethod
    def parse_ids(context: "AgentContext") -> tuple["uuid.UUID", "uuid.UUID"]:
        """Convert context string IDs to UUIDs."""
        return uuid.UUID(context.listing_id), uuid.UUID(context.tenant_id)

    @asynccontextmanager
    async def session_scope(self, context: "AgentContext"):
        """Open a DB session with transaction, yield (session, listing_id, tenant_id).

        Usage::

            async with self.session_scope(context) as (session, listing_id, tenant_id):
                listing = await session.get(Listing, listing_id)
                ...
        """
        listing_id, tenant_id = self.parse_ids(context)
        async with self._session_factory() as session:
            async with (session.begin() if not session.in_transaction() else session.begin_nested()):
                yield session, listing_id, tenant_id

    async def emit(self, session, context: "AgentContext", event_type: str, payload: dict):
        """Shorthand for emit_event with agent context."""
        from listingjet.services.events import emit_event
        await emit_event(
            session=session,
            event_type=event_type,
            payload=payload,
            tenant_id=context.tenant_id,
            listing_id=context.listing_id,
        )
