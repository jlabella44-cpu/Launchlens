from enum import Enum


class PptxExportFormatType(str, Enum):
    PPTX = "pptx"

    def __str__(self) -> str:
        return str(self.value)
