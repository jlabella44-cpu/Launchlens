from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="EdDsaJwk")


@_attrs_define
class EdDsaJwk:
    """A JSON Web Key Set (JWKS) using the Edwards-curve Digital Signature Algorithm (EdDSA), as
    described in [RFC-8037](https://www.rfc-editor.org/rfc/rfc8037.html#appendix-A).

        Attributes:
            kid (str): The `kid` (key ID) is a unique identifier for a public key. When the keys used
                to sign webhooks are rotated, you can use this ID to select the correct key
                within a JWK Set during the key rollover. The `kid` value is case-sensitive.
            kty (str): The `kty` (key type) identifies the cryptographic algorithm family used with
                the key, such as "RSA" or "EC". Only Octet Key Pairs
                (`OKPs`) are supported.
                The `kty` value is case-sensitive. For more information on the `kty` property
                and OKPs, see [RFC-8037 — "kty" (Key Type)
                Parameter](https://www.rfc-editor.org/rfc/rfc8037.html#section-2).
            crv (str): The `crv` (curve) property identifies the curve used for elliptical curve
                encryptions. Only "Ed25519" is supported. For more information on the `crv`
                property, see [RFC-8037 — Key Type
                "OKP"](https://www.rfc-editor.org/rfc/rfc8037.html#section-2).
            x (str): The `x` property is the public key of an elliptical curve encryption. The key
                is Base64urlUInt-encoded. For more information on the `x` property, see
                [RFC-8037 — "x" (X Coordinate)
                Parameter](https://www.rfc-editor.org/rfc/rfc8037#section-2).
    """

    kid: str
    kty: str
    crv: str
    x: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        kid = self.kid

        kty = self.kty

        crv = self.crv

        x = self.x

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "kid": kid,
                "kty": kty,
                "crv": crv,
                "x": x,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        kid = d.pop("kid")

        kty = d.pop("kty")

        crv = d.pop("crv")

        x = d.pop("x")

        ed_dsa_jwk = cls(
            kid=kid,
            kty=kty,
            crv=crv,
            x=x,
        )

        ed_dsa_jwk.additional_properties = d
        return ed_dsa_jwk

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
