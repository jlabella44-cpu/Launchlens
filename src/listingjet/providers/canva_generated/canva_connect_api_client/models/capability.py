from enum import Enum


class Capability(str, Enum):
    AUTOFILL = "autofill"
    BRAND_TEMPLATE = "brand_template"
    RESIZE = "resize"
    TEAM_RESTRICTED_APP = "team_restricted_app"

    def __str__(self) -> str:
        return str(self.value)
