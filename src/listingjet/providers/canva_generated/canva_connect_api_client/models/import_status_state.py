from enum import Enum


class ImportStatusState(str, Enum):
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"

    def __str__(self) -> str:
        return str(self.value)
