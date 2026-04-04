from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.design_comment_object_input import DesignCommentObjectInput


T = TypeVar("T", bound="CreateReplyRequest")


@_attrs_define
class CreateReplyRequest:
    """
    Attributes:
        attached_to (DesignCommentObjectInput): If the comment is attached to a Canva Design.
        message (str): The reply comment message. This is the reply comment body shown in the Canva UI.

            You can also mention users in your message by specifying their User ID and Team ID
            using the format `[user_id:team_id]`. Example: Thanks!.
    """

    attached_to: DesignCommentObjectInput
    message: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        attached_to = self.attached_to.to_dict()

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "attached_to": attached_to,
                "message": message,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_comment_object_input import DesignCommentObjectInput

        d = dict(src_dict)
        attached_to = DesignCommentObjectInput.from_dict(d.pop("attached_to"))

        message = d.pop("message")

        create_reply_request = cls(
            attached_to=attached_to,
            message=message,
        )

        create_reply_request.additional_properties = d
        return create_reply_request

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
