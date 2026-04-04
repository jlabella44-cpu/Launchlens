from enum import Enum


class DataTableImageUploadType(str, Enum):
    IMAGE_UPLOAD = "image_upload"

    def __str__(self) -> str:
        return str(self.value)
