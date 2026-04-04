from enum import Enum


class CreateDesignAutofillJobResultType(str, Enum):
    CREATE_DESIGN = "create_design"

    def __str__(self) -> str:
        return str(self.value)
