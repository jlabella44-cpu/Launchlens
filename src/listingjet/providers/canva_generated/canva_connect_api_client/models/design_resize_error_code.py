from enum import Enum


class DesignResizeErrorCode(str, Enum):
    CREATE_DESIGN_ERROR = "create_design_error"
    DESIGN_RESIZE_ERROR = "design_resize_error"
    THUMBNAIL_GENERATION_ERROR = "thumbnail_generation_error"
    TRIAL_QUOTA_EXCEEDED = "trial_quota_exceeded"

    def __str__(self) -> str:
        return str(self.value)
