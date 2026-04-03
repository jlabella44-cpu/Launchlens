from enum import Enum


class ReplyMentionEventContentType(str, Enum):
    REPLY = "reply"

    def __str__(self) -> str:
        return str(self.value)
