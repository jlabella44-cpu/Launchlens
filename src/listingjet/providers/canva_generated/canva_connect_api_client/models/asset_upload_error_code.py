from enum import Enum


class AssetUploadErrorCode(str, Enum):
    FETCH_FAILED = "fetch_failed"
    FILE_TOO_BIG = "file_too_big"
    IMPORT_FAILED = "import_failed"

    def __str__(self) -> str:
        return str(self.value)
