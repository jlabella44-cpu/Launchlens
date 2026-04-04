from enum import Enum


class DesignApprovalResponseNotificationContentType(str, Enum):
    DESIGN_APPROVAL_RESPONSE = "design_approval_response"

    def __str__(self) -> str:
        return str(self.value)
