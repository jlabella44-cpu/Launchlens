from enum import Enum


class ResolvedCommentEventType(str, Enum):
    RESOLVED = "resolved"

    def __str__(self) -> str:
        return str(self.value)
