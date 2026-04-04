from enum import Enum


class ThreadMentionEventContentType(str, Enum):
    THREAD = "thread"

    def __str__(self) -> str:
        return str(self.value)
