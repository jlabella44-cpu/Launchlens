from enum import Enum


class DataTableVideoUploadType(str, Enum):
    VIDEO_UPLOAD = "video_upload"

    def __str__(self) -> str:
        return str(self.value)
