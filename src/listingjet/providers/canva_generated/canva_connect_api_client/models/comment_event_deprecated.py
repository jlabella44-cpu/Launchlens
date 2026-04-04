from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.comment_event_type_enum import CommentEventTypeEnum

if TYPE_CHECKING:
    from ..models.parent_comment import ParentComment
    from ..models.reply_comment import ReplyComment


T = TypeVar("T", bound="CommentEventDeprecated")


@_attrs_define
class CommentEventDeprecated:
    """Basic details about the comment.

    The `comment` property is deprecated.
    For details of the comment event, use the `comment_event` property instead.

        Attributes:
            type_ (CommentEventTypeEnum): The type of comment event.
            data (ParentComment | ReplyComment): The comment object, which contains metadata about the comment.
                Deprecated in favor of the new `thread` object.
    """

    type_: CommentEventTypeEnum
    data: ParentComment | ReplyComment
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.parent_comment import ParentComment

        type_ = self.type_.value

        data: dict[str, Any]
        if isinstance(self.data, ParentComment):
            data = self.data.to_dict()
        else:
            data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.parent_comment import ParentComment
        from ..models.reply_comment import ReplyComment

        d = dict(src_dict)
        type_ = CommentEventTypeEnum(d.pop("type"))

        def _parse_data(data: object) -> ParentComment | ReplyComment:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_comment_type_0 = ParentComment.from_dict(data)

                return componentsschemas_comment_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_comment_type_1 = ReplyComment.from_dict(data)

            return componentsschemas_comment_type_1

        data = _parse_data(d.pop("data"))

        comment_event_deprecated = cls(
            type_=type_,
            data=data,
        )

        comment_event_deprecated.additional_properties = d
        return comment_event_deprecated

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
