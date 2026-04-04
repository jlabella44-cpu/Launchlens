from enum import Enum


class NewCommentEventType(str, Enum):
    NEW = "new"

    def __str__(self) -> str:
        return str(self.value)
