from enum import Enum


class PresetDesignTypeInputType(str, Enum):
    PRESET = "preset"

    def __str__(self) -> str:
        return str(self.value)
