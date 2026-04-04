from enum import Enum


class JpgExportFormatType(str, Enum):
    JPG = "jpg"

    def __str__(self) -> str:
        return str(self.value)
