from enum import Enum


class ParentCommentType(str, Enum):
    PARENT = "parent"

    def __str__(self) -> str:
        return str(self.value)
