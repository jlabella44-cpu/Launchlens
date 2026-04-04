from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.mention_comment_event_type import MentionCommentEventType

if TYPE_CHECKING:
    from ..models.reply_mention_event_content import ReplyMentionEventContent
    from ..models.thread_mention_event_content import ThreadMentionEventContent


T = TypeVar("T", bound="MentionCommentEvent")


@_attrs_define
class MentionCommentEvent:
    """Event type for a mention in a comment thread or reply.

    Attributes:
        type_ (MentionCommentEventType):
        content (ReplyMentionEventContent | ThreadMentionEventContent): The type of mention event content, along with
            additional type-specific properties.
    """

    type_: MentionCommentEventType
    content: ReplyMentionEventContent | ThreadMentionEventContent
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.thread_mention_event_content import ThreadMentionEventContent

        type_ = self.type_.value

        content: dict[str, Any]
        if isinstance(self.content, ThreadMentionEventContent):
            content = self.content.to_dict()
        else:
            content = self.content.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "content": content,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.reply_mention_event_content import ReplyMentionEventContent
        from ..models.thread_mention_event_content import ThreadMentionEventContent

        d = dict(src_dict)
        type_ = MentionCommentEventType(d.pop("type"))

        def _parse_content(data: object) -> ReplyMentionEventContent | ThreadMentionEventContent:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_mention_event_content_type_0 = ThreadMentionEventContent.from_dict(data)

                return componentsschemas_mention_event_content_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_mention_event_content_type_1 = ReplyMentionEventContent.from_dict(data)

            return componentsschemas_mention_event_content_type_1

        content = _parse_content(d.pop("content"))

        mention_comment_event = cls(
            type_=type_,
            content=content,
        )

        mention_comment_event.additional_properties = d
        return mention_comment_event

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
