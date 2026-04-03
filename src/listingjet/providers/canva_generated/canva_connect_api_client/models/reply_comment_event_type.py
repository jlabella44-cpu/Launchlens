from enum import Enum


class ReplyCommentEventType(str, Enum):
    REPLY = "reply"

    def __str__(self) -> str:
        return str(self.value)
