from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateThreadRequest")


@_attrs_define
class CreateThreadRequest:
    """
    Attributes:
        message_plaintext (str): The comment message in plaintext. This is the comment body shown in the Canva UI.

            You can also mention users in your message by specifying their User ID and Team ID
            using the format `[user_id:team_id]`. If the `assignee_id` parameter is specified, you
            must mention the assignee in the message. Example: Great work [oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP]!.
        assignee_id (str | Unset): Lets you assign the comment to a Canva user using their User ID. You _must_ mention
            the
            assigned user in the `message`. Example: oUnPjZ2k2yuhftbWF7873o.
    """

    message_plaintext: str
    assignee_id: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        message_plaintext = self.message_plaintext

        assignee_id = self.assignee_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "message_plaintext": message_plaintext,
            }
        )
        if assignee_id is not UNSET:
            field_dict["assignee_id"] = assignee_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        message_plaintext = d.pop("message_plaintext")

        assignee_id = d.pop("assignee_id", UNSET)

        create_thread_request = cls(
            message_plaintext=message_plaintext,
            assignee_id=assignee_id,
        )

        create_thread_request.additional_properties = d
        return create_thread_request

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
