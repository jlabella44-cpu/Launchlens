from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="UserInfoResponse")


@_attrs_define
class UserInfoResponse:
    """
    Example:
        {'sub': 'UAAAAAAAAA', 'name': 'Alice Person', 'given_name': 'Alice', 'family_name': 'Person', 'email':
            'alice.person@example.com', 'email_verified': True}

    Attributes:
        sub (str): Identifier for the End-User at the Issuer.
        name (str | Unset): End-User's full name in displayable form including all name parts, possibly including
            titles and suffixes, ordered according to the End-User's locale and preferences.
        given_name (str | Unset): Given name(s) or first name(s) of the End-User. Note that in some cultures, people can
            have multiple given names; all can be present, with the names being separated by space
            characters.
        family_name (str | Unset): Surname(s) or last name(s) of the End-User. Note that in some cultures, people can
            have
            multiple family names or no family name; all can be present, with the names being
            separated by space characters.
        email (str | Unset): End-User's preferred e-mail address. Its value MUST conform to the RFC 5322 [RFC5322]
            addr-spec syntax. The RP MUST NOT rely upon this value being unique, as discussed in
            Section 5.7.
        email_verified (bool | Unset): True if the End-User's e-mail address has been verified; otherwise false. When
            this
            Claim Value is true, this means that the OP took affirmative steps to ensure that this
            e-mail address was controlled by the End-User at the time the verification was
            performed. The means by which an e-mail address is verified is context specific,
            and dependent upon the trust framework or contractual agreements within which the
            parties are operating.
    """

    sub: str
    name: str | Unset = UNSET
    given_name: str | Unset = UNSET
    family_name: str | Unset = UNSET
    email: str | Unset = UNSET
    email_verified: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sub = self.sub

        name = self.name

        given_name = self.given_name

        family_name = self.family_name

        email = self.email

        email_verified = self.email_verified

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "sub": sub,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name
        if given_name is not UNSET:
            field_dict["given_name"] = given_name
        if family_name is not UNSET:
            field_dict["family_name"] = family_name
        if email is not UNSET:
            field_dict["email"] = email
        if email_verified is not UNSET:
            field_dict["email_verified"] = email_verified

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sub = d.pop("sub")

        name = d.pop("name", UNSET)

        given_name = d.pop("given_name", UNSET)

        family_name = d.pop("family_name", UNSET)

        email = d.pop("email", UNSET)

        email_verified = d.pop("email_verified", UNSET)

        user_info_response = cls(
            sub=sub,
            name=name,
            given_name=given_name,
            family_name=family_name,
            email=email,
            email_verified=email_verified,
        )

        user_info_response.additional_properties = d
        return user_info_response

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
