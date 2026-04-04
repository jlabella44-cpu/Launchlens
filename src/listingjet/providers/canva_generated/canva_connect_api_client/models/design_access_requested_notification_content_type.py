from enum import Enum


class DesignAccessRequestedNotificationContentType(str, Enum):
    DESIGN_ACCESS_REQUESTED = "design_access_requested"

    def __str__(self) -> str:
        return str(self.value)
