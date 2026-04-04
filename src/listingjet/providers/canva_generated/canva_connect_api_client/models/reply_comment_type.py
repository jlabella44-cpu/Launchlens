from enum import Enum


class ReplyCommentType(str, Enum):
    REPLY = "reply"

    def __str__(self) -> str:
        return str(self.value)
