from enum import Enum


class SuggestionNotificationContentType(str, Enum):
    SUGGESTION = "suggestion"

    def __str__(self) -> str:
        return str(self.value)
