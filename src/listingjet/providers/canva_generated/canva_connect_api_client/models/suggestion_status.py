from enum import Enum


class SuggestionStatus(str, Enum):
    ACCEPTED = "accepted"
    OPEN = "open"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return str(self.value)
