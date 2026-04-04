from enum import Enum


class DesignApprovalRequestedNotificationContentType(str, Enum):
    DESIGN_APPROVAL_REQUESTED = "design_approval_requested"

    def __str__(self) -> str:
        return str(self.value)
