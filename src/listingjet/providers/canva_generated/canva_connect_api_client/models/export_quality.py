from enum import Enum


class ExportQuality(str, Enum):
    PRO = "pro"
    REGULAR = "regular"

    def __str__(self) -> str:
        return str(self.value)
