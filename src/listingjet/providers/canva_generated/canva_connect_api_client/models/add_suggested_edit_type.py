from enum import Enum


class AddSuggestedEditType(str, Enum):
    ADD = "add"

    def __str__(self) -> str:
        return str(self.value)
