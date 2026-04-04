from enum import Enum


class ImageDataFieldType(str, Enum):
    IMAGE = "image"

    def __str__(self) -> str:
        return str(self.value)
