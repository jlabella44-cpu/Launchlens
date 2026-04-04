from enum import Enum


class AutofillErrorCode(str, Enum):
    AUTOFILL_ERROR = "autofill_error"
    CREATE_DESIGN_ERROR = "create_design_error"
    DESIGN_APPROVAL_ERROR = "design_approval_error"
    THUMBNAIL_GENERATION_ERROR = "thumbnail_generation_error"

    def __str__(self) -> str:
        return str(self.value)
