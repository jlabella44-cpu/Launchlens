from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.exchange_auth_code_request_grant_type import ExchangeAuthCodeRequestGrantType
from ..types import UNSET, Unset

T = TypeVar("T", bound="ExchangeAuthCodeRequest")


@_attrs_define
class ExchangeAuthCodeRequest:
    """
    Attributes:
        grant_type (ExchangeAuthCodeRequestGrantType): For exchanging an authorization code for an access token.
            Example: authorization_code.
        code_verifier (str): The `code_verifier` value that you generated when creating the user authorization URL.
            Example: i541qdcfkb4htnork0w92lnu43en99ls5a48ittv6udqgiflqon8vusojojakbq4.
        code (str): The authorization code you received after the user authorized the integration. Example: kp8nnroja7qn
            x00.opyc1p76rcbyflsxbycjqfp3ub8vzsvltpzwafy9q5l45dn5fxzhe7i7a6mg1i2t8jpsa6sebdeumkzzhicskabgevrxsssec4dvjwfvhq4g
            s3ugghguar0voiqpfb7axsapiojoter8v3w2s5s3st84jpv2l06h667iw241xngy9c8=vu1tnjp7sz.
        client_id (str | Unset): Your integration's unique ID, for authenticating the request.

            NOTE: We recommend that you use basic access authentication instead of specifying `client_id` and
            `client_secret` as body parameters.
             Example: OC-FAB12-AbCdEf.
        client_secret (str | Unset): Your integration's client secret, for authenticating the request. Begins with
            `cnvca`.

            NOTE: We recommend that you use basic access authentication instead of specifying `client_id` and
            `client_secret` as body parameters.
             Example: cnvcaAbcdefg12345_hijklm6789.
        redirect_uri (str | Unset): Only required if a redirect URL was supplied when you [created the user
            authorization URL](https://www.canva.dev/docs/connect/authentication/#create-the-authorization-url).

            Must be one of those already specified by the client. If not supplied, the first redirect_uri defined for the
            client will be used by default.
             Example: https://example.com/process-auth.
    """

    grant_type: ExchangeAuthCodeRequestGrantType
    code_verifier: str
    code: str
    client_id: str | Unset = UNSET
    client_secret: str | Unset = UNSET
    redirect_uri: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        grant_type = self.grant_type.value

        code_verifier = self.code_verifier

        code = self.code

        client_id = self.client_id

        client_secret = self.client_secret

        redirect_uri = self.redirect_uri

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "grant_type": grant_type,
                "code_verifier": code_verifier,
                "code": code,
            }
        )
        if client_id is not UNSET:
            field_dict["client_id"] = client_id
        if client_secret is not UNSET:
            field_dict["client_secret"] = client_secret
        if redirect_uri is not UNSET:
            field_dict["redirect_uri"] = redirect_uri

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        grant_type = ExchangeAuthCodeRequestGrantType(d.pop("grant_type"))

        code_verifier = d.pop("code_verifier")

        code = d.pop("code")

        client_id = d.pop("client_id", UNSET)

        client_secret = d.pop("client_secret", UNSET)

        redirect_uri = d.pop("redirect_uri", UNSET)

        exchange_auth_code_request = cls(
            grant_type=grant_type,
            code_verifier=code_verifier,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )

        exchange_auth_code_request.additional_properties = d
        return exchange_auth_code_request

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
