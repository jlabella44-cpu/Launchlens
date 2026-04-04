from enum import Enum


class DatasetImageValueType(str, Enum):
    IMAGE = "image"

    def __str__(self) -> str:
        return str(self.value)
