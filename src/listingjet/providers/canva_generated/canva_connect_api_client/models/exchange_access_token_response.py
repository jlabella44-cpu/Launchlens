from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ExchangeAccessTokenResponse")


@_attrs_define
class ExchangeAccessTokenResponse:
    """Exchange auth token to access token.

    Attributes:
        access_token (str): The bearer access token to use to authenticate to Canva Connect API endpoints. If requested
            using a `authorization_code` or `refresh_token`, this allows you to act on behalf of a user. Example:
            JagALLazU0i2ld9WW4zTO4kaG0lkvP8Y5sSO206ZwxNF4E1y3xKJKF7TzN17BXTfaNOeY0P88AeRCE6cRF7SJzvf3Sx97rA80sGHtFplFo.
        refresh_token (str): The token that you can use to refresh the access token. Example:
            JABix5nolsk9k8n2r0f8nq1gw4zjo40ht6sb4i573wgdzmkwdmiy6muh897hp0bxyab276wtgqkvtob2mg9aidt5d6rcltcbcgs101.
        token_type (str): The token type returned. This is always `Bearer`. Example: Bearer.
        expires_in (int): The expiry time (in seconds) for the access token. Example: 14400.
        scope (str | Unset): The [scopes](https://www.canva.dev/docs/connect/appendix/scopes/) that the token has been
            granted. Example: asset:read design:meta:read design:permission:read folder:read.
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    scope: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        access_token = self.access_token

        refresh_token = self.refresh_token

        token_type = self.token_type

        expires_in = self.expires_in

        scope = self.scope

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": token_type,
                "expires_in": expires_in,
            }
        )
        if scope is not UNSET:
            field_dict["scope"] = scope

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        access_token = d.pop("access_token")

        refresh_token = d.pop("refresh_token")

        token_type = d.pop("token_type")

        expires_in = d.pop("expires_in")

        scope = d.pop("scope", UNSET)

        exchange_access_token_response = cls(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=token_type,
            expires_in=expires_in,
            scope=scope,
        )

        exchange_access_token_response.additional_properties = d
        return exchange_access_token_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
