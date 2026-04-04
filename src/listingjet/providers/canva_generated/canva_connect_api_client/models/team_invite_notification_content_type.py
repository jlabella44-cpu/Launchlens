from enum import Enum


class TeamInviteNotificationContentType(str, Enum):
    TEAM_INVITE = "team_invite"

    def __str__(self) -> str:
        return str(self.value)
