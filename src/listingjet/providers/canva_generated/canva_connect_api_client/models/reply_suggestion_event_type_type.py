from enum import Enum


class ReplySuggestionEventTypeType(str, Enum):
    REPLY = "reply"

    def __str__(self) -> str:
        return str(self.value)
