from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="IntrospectTokenResponse")


@_attrs_define
class IntrospectTokenResponse:
    """Introspection result of access or refresh tokens

    Attributes:
        active (bool): Whether the access token is active.

            If `true`, the access token is valid and active. If `false`, the access token is invalid.
             Example: True.
        scope (str | Unset): The [scopes](https://www.canva.dev/docs/connect/appendix/scopes/) that the token has been
            granted. Example: asset:read design:meta:read design:permission:read folder:read.
        client (str | Unset): The ID of the client that requested the token. Example: OC-FAB12-AbCdEf.
        exp (int | Unset): The expiration time of the token, as a [Unix
            timestamp](https://en.wikipedia.org/wiki/Unix_time) in seconds. Example: 1712216144.
        iat (int | Unset): When the token was issued, as a [Unix timestamp](https://en.wikipedia.org/wiki/Unix_time) in
            seconds. Example: 1712201744.
        nbf (int | Unset): The "not before" time of the token, which specifies the time before which the access token
            most not be accepted, as a [Unix timestamp](https://en.wikipedia.org/wiki/Unix_time) in seconds. Example:
            1712201744.
        jti (str | Unset): A unique ID for the access token. Example: AbC1d-efgHIJKLMN2oPqrS.
        sub (str | Unset): The subject of the claim. This is the ID of the Canva user that the access token acts on
            behalf of.

            This is an obfuscated value, so a single user has a unique ID for each integration. If the same user authorizes
            another integration, their ID in that other integration is different.
             Example: oBCdEF1Gh2i3jkLmno-pq.
    """

    active: bool
    scope: str | Unset = UNSET
    client: str | Unset = UNSET
    exp: int | Unset = UNSET
    iat: int | Unset = UNSET
    nbf: int | Unset = UNSET
    jti: str | Unset = UNSET
    sub: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        active = self.active

        scope = self.scope

        client = self.client

        exp = self.exp

        iat = self.iat

        nbf = self.nbf

        jti = self.jti

        sub = self.sub

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "active": active,
            }
        )
        if scope is not UNSET:
            field_dict["scope"] = scope
        if client is not UNSET:
            field_dict["client"] = client
        if exp is not UNSET:
            field_dict["exp"] = exp
        if iat is not UNSET:
            field_dict["iat"] = iat
        if nbf is not UNSET:
            field_dict["nbf"] = nbf
        if jti is not UNSET:
            field_dict["jti"] = jti
        if sub is not UNSET:
            field_dict["sub"] = sub

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        active = d.pop("active")

        scope = d.pop("scope", UNSET)

        client = d.pop("client", UNSET)

        exp = d.pop("exp", UNSET)

        iat = d.pop("iat", UNSET)

        nbf = d.pop("nbf", UNSET)

        jti = d.pop("jti", UNSET)

        sub = d.pop("sub", UNSET)

        introspect_token_response = cls(
            active=active,
            scope=scope,
            client=client,
            exp=exp,
            iat=iat,
            nbf=nbf,
            jti=jti,
            sub=sub,
        )

        introspect_token_response.additional_properties = d
        return introspect_token_response

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
