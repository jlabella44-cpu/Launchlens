from enum import Enum


class FolderItemSortBy(str, Enum):
    CREATED_ASCENDING = "created_ascending"
    CREATED_DESCENDING = "created_descending"
    MODIFIED_ASCENDING = "modified_ascending"
    MODIFIED_DESCENDING = "modified_descending"
    TITLE_ASCENDING = "title_ascending"
    TITLE_DESCENDING = "title_descending"

    def __str__(self) -> str:
        return str(self.value)
