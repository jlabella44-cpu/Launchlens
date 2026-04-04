from enum import Enum


class VideoMetadataType(str, Enum):
    VIDEO = "video"

    def __str__(self) -> str:
        return str(self.value)
