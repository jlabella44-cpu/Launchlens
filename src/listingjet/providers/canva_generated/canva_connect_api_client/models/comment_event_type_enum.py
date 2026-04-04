from enum import Enum


class CommentEventTypeEnum(str, Enum):
    ASSIGN = "assign"
    COMMENT = "comment"
    MENTION = "mention"
    REPLY = "reply"
    RESOLVE = "resolve"

    def __str__(self) -> str:
        return str(self.value)
