from enum import Enum


class DataTableAiDisclosure(str, Enum):
    APP_GENERATED = "app_generated"
    NONE = "none"

    def __str__(self) -> str:
        return str(self.value)
