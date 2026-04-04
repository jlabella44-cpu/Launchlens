from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.parent_comment_type import ParentCommentType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_comment_object import DesignCommentObject
    from ..models.parent_comment_mentions import ParentCommentMentions
    from ..models.user import User


T = TypeVar("T", bound="ParentComment")


@_attrs_define
class ParentComment:
    """Data about the comment, including the message, author, and
    the object (such as a design) the comment is attached to.

        Attributes:
            type_ (ParentCommentType):
            id (str): The ID of the comment.

                You can use this ID to create replies to the comment using the [Create reply
                API](https://www.canva.dev/docs/connect/api-reference/comments/create-reply/). Example: KeAbiEAjZEj.
            message (str): The comment message. This is the comment body shown in the Canva UI.
                User mentions are shown here in the format `[user_id:team_id]`. Example: Great work
                [oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP]!.
            author (User): Metadata for the user, consisting of the User ID and display name.
            mentions (ParentCommentMentions): The Canva users mentioned in the comment. Example:
                {'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP': {'user_id': 'oUnPjZ2k2yuhftbWF7873o', 'team_id':
                'oBpVhLW22VrqtwKgaayRbP', 'display_name': 'John Doe'}}.
            attached_to (DesignCommentObject | Unset): If the comment is attached to a Canva Design.
            created_at (int | Unset): When the comment or reply was created, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692928800.
            updated_at (int | Unset): When the comment or reply was last updated, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692928900.
            assignee (User | Unset): Metadata for the user, consisting of the User ID and display name.
            resolver (User | Unset): Metadata for the user, consisting of the User ID and display name.
    """

    type_: ParentCommentType
    id: str
    message: str
    author: User
    mentions: ParentCommentMentions
    attached_to: DesignCommentObject | Unset = UNSET
    created_at: int | Unset = UNSET
    updated_at: int | Unset = UNSET
    assignee: User | Unset = UNSET
    resolver: User | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = self.id

        message = self.message

        author = self.author.to_dict()

        mentions = self.mentions.to_dict()

        attached_to: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attached_to, Unset):
            attached_to = self.attached_to.to_dict()

        created_at = self.created_at

        updated_at = self.updated_at

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
                "id": id,
                "message": message,
                "author": author,
                "mentions": mentions,
            }
        )
        if attached_to is not UNSET:
            field_dict["attached_to"] = attached_to
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if assignee is not UNSET:
            field_dict["assignee"] = assignee
        if resolver is not UNSET:
            field_dict["resolver"] = resolver

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_comment_object import DesignCommentObject
        from ..models.parent_comment_mentions import ParentCommentMentions
        from ..models.user import User

        d = dict(src_dict)
        type_ = ParentCommentType(d.pop("type"))

        id = d.pop("id")

        message = d.pop("message")

        author = User.from_dict(d.pop("author"))

        mentions = ParentCommentMentions.from_dict(d.pop("mentions"))

        _attached_to = d.pop("attached_to", UNSET)
        attached_to: DesignCommentObject | Unset
        if isinstance(_attached_to, Unset):
            attached_to = UNSET
        else:
            attached_to = DesignCommentObject.from_dict(_attached_to)

        created_at = d.pop("created_at", UNSET)

        updated_at = d.pop("updated_at", UNSET)

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

        parent_comment = cls(
            type_=type_,
            id=id,
            message=message,
            author=author,
            mentions=mentions,
            attached_to=attached_to,
            created_at=created_at,
            updated_at=updated_at,
            assignee=assignee,
            resolver=resolver,
        )

        parent_comment.additional_properties = d
        return parent_comment

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
