from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.reply import Reply


T = TypeVar("T", bound="GetReplyResponse")


@_attrs_define
class GetReplyResponse:
    """Successful response from a `getReply` request.

    Attributes:
        reply (Reply): A reply to a thread.

            The `author` of the reply might be missing if that user account no longer exists.
    """

    reply: Reply
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        reply = self.reply.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "reply": reply,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.reply import Reply

        d = dict(src_dict)
        reply = Reply.from_dict(d.pop("reply"))

        get_reply_response = cls(
            reply=reply,
        )

        get_reply_response.additional_properties = d
        return get_reply_response

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
