from enum import Enum


class DataTableVideoMimeType(str, Enum):
    APPLICATIONJSON = "application/json"
    IMAGEGIF = "image/gif"
    VIDEOAVI = "video/avi"
    VIDEOMP4 = "video/mp4"
    VIDEOMPEG = "video/mpeg"
    VIDEOQUICKTIME = "video/quicktime"
    VIDEOWEBM = "video/webm"
    VIDEOX_M4V = "video/x-m4v"
    VIDEOX_MATROSKA = "video/x-matroska"
    VIDEOX_MSVIDEO = "video/x-msvideo"

    def __str__(self) -> str:
        return str(self.value)
