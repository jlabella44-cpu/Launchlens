from enum import Enum


class ImageItemType(str, Enum):
    IMAGE = "image"

    def __str__(self) -> str:
        return str(self.value)
