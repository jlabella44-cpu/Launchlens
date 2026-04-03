from enum import Enum


class PdfExportFormatType(str, Enum):
    PDF = "pdf"

    def __str__(self) -> str:
        return str(self.value)
