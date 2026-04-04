from enum import Enum


class AcceptedSuggestionEventTypeType(str, Enum):
    ACCEPTED = "accepted"

    def __str__(self) -> str:
        return str(self.value)
