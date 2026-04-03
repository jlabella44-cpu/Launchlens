from enum import Enum


class StringDataTableCellType(str, Enum):
    STRING = "string"

    def __str__(self) -> str:
        return str(self.value)
