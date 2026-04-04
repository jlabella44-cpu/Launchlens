from enum import Enum


class ShareFolderNotificationContentType(str, Enum):
    SHARE_FOLDER = "share_folder"

    def __str__(self) -> str:
        return str(self.value)
