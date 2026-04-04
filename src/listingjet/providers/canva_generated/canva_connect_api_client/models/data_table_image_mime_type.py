from enum import Enum


class DataTableImageMimeType(str, Enum):
    IMAGEHEIC = "image/heic"
    IMAGEJPEG = "image/jpeg"
    IMAGEPNG = "image/png"
    IMAGESVGXML = "image/svg+xml"
    IMAGETIFF = "image/tiff"
    IMAGEWEBP = "image/webp"

    def __str__(self) -> str:
        return str(self.value)
