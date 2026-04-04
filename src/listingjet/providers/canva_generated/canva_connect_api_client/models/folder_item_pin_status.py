from enum import Enum


class FolderItemPinStatus(str, Enum):
    ANY = "any"
    PINNED = "pinned"

    def __str__(self) -> str:
        return str(self.value)
