from enum import Enum


class Mp4ExportFormatType(str, Enum):
    MP4 = "mp4"

    def __str__(self) -> str:
        return str(self.value)
