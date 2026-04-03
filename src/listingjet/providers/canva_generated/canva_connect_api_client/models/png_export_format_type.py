from enum import Enum


class PngExportFormatType(str, Enum):
    PNG = "png"

    def __str__(self) -> str:
        return str(self.value)
