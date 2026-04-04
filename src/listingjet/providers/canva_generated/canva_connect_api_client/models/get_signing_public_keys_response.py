from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.ed_dsa_jwk import EdDsaJwk


T = TypeVar("T", bound="GetSigningPublicKeysResponse")


@_attrs_define
class GetSigningPublicKeysResponse:
    """
    Attributes:
        keys (list[EdDsaJwk]): A Json Web Key Set (JWKS) with public keys used for signing webhooks. You can use this
            JWKS
            to verify that a webhook was sent from Canva. Example: [{'kid': 'a418dc7d-ecc5-5c4b-85ce-e1104a8addbe', 'kty':
            'OKP', 'crv': 'Ed25519', 'x': 'aIQtqd0nDfB-ug0DrzZbwTum-1ITdXvKxGFak_1VB2j'}, {'kid':
            'c8de5bec1-1b88-4ddaae04acc-ce415-5d7', 'kty': 'OKP', 'crv': 'Ed25519', 'x': 'm2d1FT-
            gfBXxIzKwdQVTra0D-aBq_ubZ1jI0GuvkDtn'}].
    """

    keys: list[EdDsaJwk]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        keys = []
        for keys_item_data in self.keys:
            keys_item = keys_item_data.to_dict()
            keys.append(keys_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "keys": keys,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ed_dsa_jwk import EdDsaJwk

        d = dict(src_dict)
        keys = []
        _keys = d.pop("keys")
        for keys_item_data in _keys:
            keys_item = EdDsaJwk.from_dict(keys_item_data)

            keys.append(keys_item)

        get_signing_public_keys_response = cls(
            keys=keys,
        )

        get_signing_public_keys_response.additional_properties = d
        return get_signing_public_keys_response

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
