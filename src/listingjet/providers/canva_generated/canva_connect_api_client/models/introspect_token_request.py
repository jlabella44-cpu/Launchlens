from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="IntrospectTokenRequest")


@_attrs_define
class IntrospectTokenRequest:
    """
    Attributes:
        token (str): The token to introspect. Example:
            JagALLazU0i2ld9WW4zTO4kaG0lkvP8Y5sSO206ZwxNF4E1y3xKJKF7TzN17BXTfaNOeY0P88AeRCE6cRF7SJzvf3Sx97rA80sGHtFplFo.
        client_id (str | Unset): Your integration's unique ID, for authenticating the request.

            NOTE: We recommend that you use basic access authentication instead of specifying `client_id` and
            `client_secret` as body parameters.
             Example: OC-FAB12-AbCdEf.
        client_secret (str | Unset): Your integration's client secret, for authenticating the request. Begins with
            `cnvca`.

            NOTE: We recommend that you use basic access authentication instead of specifying `client_id` and
            `client_secret` as body parameters.
             Example: cnvcaAbcdefg12345_hijklm6789.
    """

    token: str
    client_id: str | Unset = UNSET
    client_secret: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        token = self.token

        client_id = self.client_id

        client_secret = self.client_secret

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "token": token,
            }
        )
        if client_id is not UNSET:
            field_dict["client_id"] = client_id
        if client_secret is not UNSET:
            field_dict["client_secret"] = client_secret

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        token = d.pop("token")

        client_id = d.pop("client_id", UNSET)

        client_secret = d.pop("client_secret", UNSET)

        introspect_token_request = cls(
            token=token,
            client_id=client_id,
            client_secret=client_secret,
        )

        introspect_token_request.additional_properties = d
        return introspect_token_request

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
