from enum import Enum


class ExchangeRefreshTokenRequestGrantType(str, Enum):
    REFRESH_TOKEN = "refresh_token"

    def __str__(self) -> str:
        return str(self.value)
