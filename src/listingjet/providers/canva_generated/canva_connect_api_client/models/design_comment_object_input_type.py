from enum import Enum


class DesignCommentObjectInputType(str, Enum):
    DESIGN = "design"

    def __str__(self) -> str:
        return str(self.value)
