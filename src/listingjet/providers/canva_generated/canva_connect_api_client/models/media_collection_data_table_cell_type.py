from enum import Enum


class MediaCollectionDataTableCellType(str, Enum):
    MEDIA = "media"

    def __str__(self) -> str:
        return str(self.value)
