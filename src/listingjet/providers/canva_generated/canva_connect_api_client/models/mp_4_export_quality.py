from enum import Enum


class Mp4ExportQuality(str, Enum):
    HORIZONTAL_1080P = "horizontal_1080p"
    HORIZONTAL_480P = "horizontal_480p"
    HORIZONTAL_4K = "horizontal_4k"
    HORIZONTAL_720P = "horizontal_720p"
    VERTICAL_1080P = "vertical_1080p"
    VERTICAL_480P = "vertical_480p"
    VERTICAL_4K = "vertical_4k"
    VERTICAL_720P = "vertical_720p"

    def __str__(self) -> str:
        return str(self.value)
