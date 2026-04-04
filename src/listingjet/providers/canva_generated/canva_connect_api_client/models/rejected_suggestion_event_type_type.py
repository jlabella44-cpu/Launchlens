from enum import Enum


class RejectedSuggestionEventTypeType(str, Enum):
    REJECTED = "rejected"

    def __str__(self) -> str:
        return str(self.value)
