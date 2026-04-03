from enum import Enum


class PresetDesignTypeName(str, Enum):
    DOC = "doc"
    PRESENTATION = "presentation"
    WHITEBOARD = "whiteboard"

    def __str__(self) -> str:
        return str(self.value)
