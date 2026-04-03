from enum import Enum


class ColumnDataType(str, Enum):
    BOOLEAN = "boolean"
    DATE = "date"
    MEDIA = "media"
    NUMBER = "number"
    STRING = "string"
    VARIANT = "variant"

    def __str__(self) -> str:
        return str(self.value)
