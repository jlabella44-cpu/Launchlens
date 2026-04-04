from enum import Enum


class NewSuggestionEventTypeType(str, Enum):
    NEW = "new"

    def __str__(self) -> str:
        return str(self.value)
