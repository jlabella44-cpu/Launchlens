from enum import Enum


class BooleanDataTableCellType(str, Enum):
    BOOLEAN = "boolean"

    def __str__(self) -> str:
        return str(self.value)
