from enum import Enum


class DeleteSuggestedEditType(str, Enum):
    DELETE = "delete"

    def __str__(self) -> str:
        return str(self.value)
