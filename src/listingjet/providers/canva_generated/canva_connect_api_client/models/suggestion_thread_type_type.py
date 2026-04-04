from enum import Enum


class SuggestionThreadTypeType(str, Enum):
    SUGGESTION = "suggestion"

    def __str__(self) -> str:
        return str(self.value)
