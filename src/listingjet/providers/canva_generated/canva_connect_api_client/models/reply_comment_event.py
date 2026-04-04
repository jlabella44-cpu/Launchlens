from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.reply_comment_event_type import ReplyCommentEventType

if TYPE_CHECKING:
    from ..models.reply import Reply


T = TypeVar("T", bound="ReplyCommentEvent")


@_attrs_define
class ReplyCommentEvent:
    """Event type for a reply to a comment thread.

    Attributes:
        type_ (ReplyCommentEventType):
        reply_url (str): A URL to the design, focused on the comment reply. Example:
            https://www.canva.com/design/3WCduQdjayTcPVM/z128cqanFu7E3/edit?ui=OdllGgZ4Snnq3MD8uI10bfA.
        reply (Reply): A reply to a thread.

            The `author` of the reply might be missing if that user account no longer exists.
    """

    type_: ReplyCommentEventType
    reply_url: str
    reply: Reply
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        reply_url = self.reply_url

        reply = self.reply.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "reply_url": reply_url,
                "reply": reply,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.reply import Reply

        d = dict(src_dict)
        type_ = ReplyCommentEventType(d.pop("type"))

        reply_url = d.pop("reply_url")

        reply = Reply.from_dict(d.pop("reply"))

        reply_comment_event = cls(
            type_=type_,
            reply_url=reply_url,
            reply=reply,
        )

        reply_comment_event.additional_properties = d
        return reply_comment_event

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
