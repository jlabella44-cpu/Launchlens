from enum import Enum


class GifExportFormatType(str, Enum):
    GIF = "gif"

    def __str__(self) -> str:
        return str(self.value)
