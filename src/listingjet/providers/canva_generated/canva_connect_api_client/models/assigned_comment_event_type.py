from enum import Enum


class AssignedCommentEventType(str, Enum):
    ASSIGNED = "assigned"

    def __str__(self) -> str:
        return str(self.value)
