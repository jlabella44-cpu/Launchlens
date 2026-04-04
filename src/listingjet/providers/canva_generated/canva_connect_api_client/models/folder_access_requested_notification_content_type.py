from enum import Enum


class FolderAccessRequestedNotificationContentType(str, Enum):
    FOLDER_ACCESS_REQUESTED = "folder_access_requested"

    def __str__(self) -> str:
        return str(self.value)
