from enum import Enum


class MentionSuggestionEventTypeType(str, Enum):
    MENTION = "mention"

    def __str__(self) -> str:
        return str(self.value)
