from enum import Enum


class ExportPageSize(str, Enum):
    A3 = "a3"
    A4 = "a4"
    LEGAL = "legal"
    LETTER = "letter"

    def __str__(self) -> str:
        return str(self.value)
