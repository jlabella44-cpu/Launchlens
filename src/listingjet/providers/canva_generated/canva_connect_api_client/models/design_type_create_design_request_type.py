from enum import Enum


class DesignTypeCreateDesignRequestType(str, Enum):
    TYPE_AND_ASSET = "type_and_asset"

    def __str__(self) -> str:
        return str(self.value)
