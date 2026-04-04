from enum import Enum


class DesignImportErrorCode(str, Enum):
    DESIGN_CREATION_THROTTLED = "design_creation_throttled"
    DESIGN_IMPORT_THROTTLED = "design_import_throttled"
    DUPLICATE_IMPORT = "duplicate_import"
    FETCH_FAILED = "fetch_failed"
    INTERNAL_ERROR = "internal_error"
    INVALID_FILE = "invalid_file"

    def __str__(self) -> str:
        return str(self.value)
