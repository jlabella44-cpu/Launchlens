from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="JsonWebKey")


@_attrs_define
class JsonWebKey:
    """Standard Json Web Key specification following https://www.rfc-editor.org/rfc/rfc7517 and
    https://www.rfc-editor.org/rfc/rfc7518.html.

        Attributes:
            kid (str): The "kid" (key ID) parameter is used to match a specific key.  This
                is used, for instance, to choose among a set of keys within a JWK Set
                during key rollover. When "kid" values are used within a JWK Set,
                different keys within the JWK Set SHOULD use distinct "kid" values.
                The "kid" value is a case-sensitive string.
                See https://www.rfc-editor.org/rfc/rfc7517#section-4
            kty (str): The "kty" (key type) parameter identifies the cryptographic algorithm
                family used with the key, such as "RSA" or "EC". The "kty" value is a
                case-sensitive string. At the moment, only "RSA" is supported.
                See https://www.rfc-editor.org/rfc/rfc7517#section-4
            n (str): The "n" (modulus) parameter contains the modulus value for the RSA
                   public key.  It is represented as a Base64urlUInt-encoded value.
                See https://www.rfc-editor.org/rfc/rfc7518.html#section-6.3
            e (str): The "e" (exponent) parameter contains the exponent value for the RSA
                   public key.  It is represented as a Base64urlUInt-encoded value.
                See https://www.rfc-editor.org/rfc/rfc7518.html#section-6.3
            alg (str | Unset): The "alg" (algorithm) parameter identifies the algorithm intended for
                use with the key.
                See https://www.rfc-editor.org/rfc/rfc7517#section-4
            use (str | Unset): The "use" (public key use) parameter identifies the intended use of
                the public key. The "use" parameter is employed to indicate whether
                a public key is used for encrypting data or verifying the signature
                on data. Values are commonly "sig" (signature) or "enc" (encryption).
                See https://www.rfc-editor.org/rfc/rfc7517#section-4
    """

    kid: str
    kty: str
    n: str
    e: str
    alg: str | Unset = UNSET
    use: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        kid = self.kid

        kty = self.kty

        n = self.n

        e = self.e

        alg = self.alg

        use = self.use

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "kid": kid,
                "kty": kty,
                "n": n,
                "e": e,
            }
        )
        if alg is not UNSET:
            field_dict["alg"] = alg
        if use is not UNSET:
            field_dict["use"] = use

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        kid = d.pop("kid")

        kty = d.pop("kty")

        n = d.pop("n")

        e = d.pop("e")

        alg = d.pop("alg", UNSET)

        use = d.pop("use", UNSET)

        json_web_key = cls(
            kid=kid,
            kty=kty,
            n=n,
            e=e,
            alg=alg,
            use=use,
        )

        json_web_key.additional_properties = d
        return json_web_key

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
