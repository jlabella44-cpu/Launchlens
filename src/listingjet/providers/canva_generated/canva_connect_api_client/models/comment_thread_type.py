from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.comment_thread_type_type import CommentThreadTypeType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.comment_content import CommentContent
    from ..models.comment_thread_type_mentions import CommentThreadTypeMentions
    from ..models.user import User


T = TypeVar("T", bound="CommentThreadType")


@_attrs_define
class CommentThreadType:
    """A comment thread.

    Attributes:
        type_ (CommentThreadTypeType):
        content (CommentContent): The content of a comment thread or reply.
        mentions (CommentThreadTypeMentions): The Canva users mentioned in the comment thread or reply. Example:
            {'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP': {'tag': 'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP',
            'user': {'user_id': 'oUnPjZ2k2yuhftbWF7873o', 'team_id': 'oBpVhLW22VrqtwKgaayRbP', 'display_name': 'John
            Doe'}}}.
        assignee (User | Unset): Metadata for the user, consisting of the User ID and display name.
        resolver (User | Unset): Metadata for the user, consisting of the User ID and display name.
    """

    type_: CommentThreadTypeType
    content: CommentContent
    mentions: CommentThreadTypeMentions
    assignee: User | Unset = UNSET
    resolver: User | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        content = self.content.to_dict()

        mentions = self.mentions.to_dict()

        assignee: dict[str, Any] | Unset = UNSET
        if not isinstance(self.assignee, Unset):
            assignee = self.assignee.to_dict()

        resolver: dict[str, Any] | Unset = UNSET
        if not isinstance(self.resolver, Unset):
            resolver = self.resolver.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "content": content,
                "mentions": mentions,
            }
        )
        if assignee is not UNSET:
            field_dict["assignee"] = assignee
        if resolver is not UNSET:
            field_dict["resolver"] = resolver

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.comment_content import CommentContent
        from ..models.comment_thread_type_mentions import CommentThreadTypeMentions
        from ..models.user import User

        d = dict(src_dict)
        type_ = CommentThreadTypeType(d.pop("type"))

        content = CommentContent.from_dict(d.pop("content"))

        mentions = CommentThreadTypeMentions.from_dict(d.pop("mentions"))

        _assignee = d.pop("assignee", UNSET)
        assignee: User | Unset
        if isinstance(_assignee, Unset):
            assignee = UNSET
        else:
            assignee = User.from_dict(_assignee)

        _resolver = d.pop("resolver", UNSET)
        resolver: User | Unset
        if isinstance(_resolver, Unset):
            resolver = UNSET
        else:
            resolver = User.from_dict(_resolver)

        comment_thread_type = cls(
            type_=type_,
            content=content,
            mentions=mentions,
            assignee=assignee,
            resolver=resolver,
        )

        comment_thread_type.additional_properties = d
        return comment_thread_type

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
