from enum import Enum


class FolderItemType(str, Enum):
    DESIGN = "design"
    FOLDER = "folder"
    IMAGE = "image"

    def __str__(self) -> str:
        return str(self.value)
