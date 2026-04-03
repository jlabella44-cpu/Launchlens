from enum import Enum


class DesignApprovalReviewerInvalidatedNotificationContentType(str, Enum):
    DESIGN_APPROVAL_REVIEWER_INVALIDATED = "design_approval_reviewer_invalidated"

    def __str__(self) -> str:
        return str(self.value)
