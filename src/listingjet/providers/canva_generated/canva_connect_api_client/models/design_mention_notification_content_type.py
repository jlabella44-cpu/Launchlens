from enum import Enum


class DesignMentionNotificationContentType(str, Enum):
    DESIGN_MENTION = "design_mention"

    def __str__(self) -> str:
        return str(self.value)
