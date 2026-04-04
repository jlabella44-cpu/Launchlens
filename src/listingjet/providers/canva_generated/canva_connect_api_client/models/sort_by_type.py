from enum import Enum


class SortByType(str, Enum):
    MODIFIED_ASCENDING = "modified_ascending"
    MODIFIED_DESCENDING = "modified_descending"
    RELEVANCE = "relevance"
    TITLE_ASCENDING = "title_ascending"
    TITLE_DESCENDING = "title_descending"

    def __str__(self) -> str:
        return str(self.value)
