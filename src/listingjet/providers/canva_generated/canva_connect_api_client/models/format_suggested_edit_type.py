from enum import Enum


class FormatSuggestedEditType(str, Enum):
    FORMAT = "format"

    def __str__(self) -> str:
        return str(self.value)
