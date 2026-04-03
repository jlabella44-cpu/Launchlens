from enum import Enum


class ShareDesignNotificationContentType(str, Enum):
    SHARE_DESIGN = "share_design"

    def __str__(self) -> str:
        return str(self.value)
