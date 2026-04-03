from enum import Enum


class CommentThreadTypeType(str, Enum):
    COMMENT = "comment"

    def __str__(self) -> str:
        return str(self.value)
