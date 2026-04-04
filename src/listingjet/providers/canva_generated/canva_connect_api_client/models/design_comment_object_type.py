from enum import Enum


class DesignCommentObjectType(str, Enum):
    DESIGN = "design"

    def __str__(self) -> str:
        return str(self.value)
