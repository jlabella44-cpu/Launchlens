from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_comment_object_input import DesignCommentObjectInput


T = TypeVar("T", bound="CreateCommentRequest")


@_attrs_define
class CreateCommentRequest:
    """
    Attributes:
        attached_to (DesignCommentObjectInput): If the comment is attached to a Canva Design.
        message (str): The comment message. This is the comment body shown in the Canva UI.

            You can also mention users in your message by specifying their User ID and Team ID
            using the format `[user_id:team_id]`. If the `assignee_id` parameter is specified, you
            must mention the assignee in the message. Example: Great work [oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP]!.
        assignee_id (str | Unset): Lets you assign the comment to a Canva user using their User ID. You _must_ mention
            the
            assigned user in the `message`. Example: oUnPjZ2k2yuhftbWF7873o.
    """

    attached_to: DesignCommentObjectInput
    message: str
    assignee_id: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attached_to = self.attached_to.to_dict()

        message = self.message

        assignee_id = self.assignee_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "attached_to": attached_to,
                "message": message,
            }
        )
        if assignee_id is not UNSET:
            field_dict["assignee_id"] = assignee_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_comment_object_input import DesignCommentObjectInput

        d = dict(src_dict)
        attached_to = DesignCommentObjectInput.from_dict(d.pop("attached_to"))

        message = d.pop("message")

        assignee_id = d.pop("assignee_id", UNSET)

        create_comment_request = cls(
            attached_to=attached_to,
            message=message,
            assignee_id=assignee_id,
        )

        create_comment_request.additional_properties = d
        return create_comment_request

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
