from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.exchange_refresh_token_request_grant_type import ExchangeRefreshTokenRequestGrantType
from ..types import UNSET, Unset

T = TypeVar("T", bound="ExchangeRefreshTokenRequest")


@_attrs_define
class ExchangeRefreshTokenRequest:
    """
    Attributes:
        grant_type (ExchangeRefreshTokenRequestGrantType): For generating an access token using a refresh token.
            Example: refresh_token.
        refresh_token (str): The refresh token to be exchanged. You can copy this value from the successful response
            received when generating an access token. Example:
            JABix5nolsk9k8n2r0f8nq1gw4zjo40ht6sb4i573wgdzmkwdmiy6muh897hp0bxyab276wtgqkvtob2mg9aidt5d6rcltcbcgs101.
        client_id (str | Unset): Your integration's unique ID, for authenticating the request.

            NOTE: We recommend that you use basic access authentication instead of specifying `client_id` and
            `client_secret` as body parameters.
             Example: OC-FAB12-AbCdEf.
        client_secret (str | Unset): Your integration's client secret, for authenticating the request. Begins with
            `cnvca`.

            NOTE: We recommend that you use basic access authentication instead of specifying `client_id` and
            `client_secret` as body parameters.
             Example: cnvcaAbcdefg12345_hijklm6789.
        scope (str | Unset): Optional scope value when refreshing an access token. Separate multiple
            [scopes](https://www.canva.dev/docs/connect/appendix/scopes/) with a single space between each scope.

            The requested scope cannot include any permissions not already granted, so this parameter allows you to limit
            the scope when refreshing a token. If omitted, the scope for the token remains unchanged.
             Example: design:meta:read.
    """

    grant_type: ExchangeRefreshTokenRequestGrantType
    refresh_token: str
    client_id: str | Unset = UNSET
    client_secret: str | Unset = UNSET
    scope: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        grant_type = self.grant_type.value

        refresh_token = self.refresh_token

        client_id = self.client_id

        client_secret = self.client_secret

        scope = self.scope

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "grant_type": grant_type,
                "refresh_token": refresh_token,
            }
        )
        if client_id is not UNSET:
            field_dict["client_id"] = client_id
        if client_secret is not UNSET:
            field_dict["client_secret"] = client_secret
        if scope is not UNSET:
            field_dict["scope"] = scope

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        grant_type = ExchangeRefreshTokenRequestGrantType(d.pop("grant_type"))

        refresh_token = d.pop("refresh_token")

        client_id = d.pop("client_id", UNSET)

        client_secret = d.pop("client_secret", UNSET)

        scope = d.pop("scope", UNSET)

        exchange_refresh_token_request = cls(
            grant_type=grant_type,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
        )

        exchange_refresh_token_request.additional_properties = d
        return exchange_refresh_token_request

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
