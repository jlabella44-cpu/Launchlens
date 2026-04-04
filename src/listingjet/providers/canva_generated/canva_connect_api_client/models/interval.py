from enum import Enum


class Interval(str, Enum):
    DAY = "day"
    MONTH = "month"
    NEVER = "never"
    WEEK = "week"
    YEAR = "year"

    def __str__(self) -> str:
        return str(self.value)
