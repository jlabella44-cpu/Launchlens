from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.mention_suggestion_event_type_type import MentionSuggestionEventTypeType

if TYPE_CHECKING:
    from ..models.reply import Reply


T = TypeVar("T", bound="MentionSuggestionEventType")


@_attrs_define
class MentionSuggestionEventType:
    """Event type for a mention in a reply to a suggestion.

    Attributes:
        type_ (MentionSuggestionEventTypeType):
        reply_url (str): A URL to the design, focused on the suggestion reply. Example:
            https://www.canva.com/design/3WCduQdjayTcPVM/z128cqanFu7E3/edit?ui=OdllGgZ4Snnq3MD8uI10bfA.
        reply (Reply): A reply to a thread.

            The `author` of the reply might be missing if that user account no longer exists.
    """

    type_: MentionSuggestionEventTypeType
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
        type_ = MentionSuggestionEventTypeType(d.pop("type"))

        reply_url = d.pop("reply_url")

        reply = Reply.from_dict(d.pop("reply"))

        mention_suggestion_event_type = cls(
            type_=type_,
            reply_url=reply_url,
            reply=reply,
        )

        mention_suggestion_event_type.additional_properties = d
        return mention_suggestion_event_type

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
