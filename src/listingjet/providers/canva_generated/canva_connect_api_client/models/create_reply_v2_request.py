from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CreateReplyV2Request")


@_attrs_define
class CreateReplyV2Request:
    """
    Attributes:
        message_plaintext (str): The comment message of the reply in plaintext. This is the reply comment shown in the
            Canva UI.

            You can also mention users in your message by specifying their User ID and Team ID
            using the format `[user_id:team_id]`. Example: Thanks!.
    """

    message_plaintext: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        message_plaintext = self.message_plaintext

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "message_plaintext": message_plaintext,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        message_plaintext = d.pop("message_plaintext")

        create_reply_v2_request = cls(
            message_plaintext=message_plaintext,
        )

        create_reply_v2_request.additional_properties = d
        return create_reply_v2_request

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
