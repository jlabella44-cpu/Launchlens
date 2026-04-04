from enum import Enum


class ExportErrorCode(str, Enum):
    APPROVAL_REQUIRED = "approval_required"
    INTERNAL_FAILURE = "internal_failure"
    LICENSE_REQUIRED = "license_required"

    def __str__(self) -> str:
        return str(self.value)
