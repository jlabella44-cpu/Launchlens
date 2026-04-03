from enum import Enum


class DatasetFilter(str, Enum):
    ANY = "any"
    NON_EMPTY = "non_empty"

    def __str__(self) -> str:
        return str(self.value)
