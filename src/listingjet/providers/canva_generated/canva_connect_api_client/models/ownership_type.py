from enum import Enum


class OwnershipType(str, Enum):
    ANY = "any"
    OWNED = "owned"
    SHARED = "shared"

    def __str__(self) -> str:
        return str(self.value)
