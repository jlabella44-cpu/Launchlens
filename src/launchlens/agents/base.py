from abc import ABC, abstractmethod
from dataclasses import dataclass


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

    async def handle_failure(self, error: Exception, context: "AgentContext", session=None) -> None:
        """
        Emit a failure event and re-raise so Temporal retries the activity.
        session is optional — if None, failure is logged but not persisted.
        """
        if session is not None:
            from launchlens.services.events import emit_event
            await emit_event(
                session=session,
                event_type=f"{self.agent_name}.failed",
                payload={"error": str(error), "error_type": type(error).__name__},
                tenant_id=str(context.tenant_id),
                listing_id=str(context.listing_id) if context.listing_id else None,
            )
        raise error  # Temporal sees the failure and applies retry policy
