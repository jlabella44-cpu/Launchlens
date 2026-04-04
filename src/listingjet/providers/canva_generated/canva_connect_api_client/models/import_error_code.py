from enum import Enum


class ImportErrorCode(str, Enum):
    FILE_TOO_BIG = "file_too_big"
    IMPORT_FAILED = "import_failed"

    def __str__(self) -> str:
        return str(self.value)
