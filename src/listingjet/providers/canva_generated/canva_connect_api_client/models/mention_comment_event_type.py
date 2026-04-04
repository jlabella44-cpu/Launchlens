from enum import Enum


class MentionCommentEventType(str, Enum):
    MENTION = "mention"

    def __str__(self) -> str:
        return str(self.value)
