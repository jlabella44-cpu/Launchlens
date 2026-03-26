from abc import ABC, abstractmethod
from dataclasses import dataclass
from launchlens.services.events import emit_event


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

    async def handle_failure(self, error: Exception, context: AgentContext) -> None:
        await emit_event(
            f"{self.agent_name}.failed",
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "listing_id": context.listing_id,
                "tenant_id": context.tenant_id,
            },
        )
        raise error  # Temporal sees the failure and applies retry policy
