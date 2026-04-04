from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.reply_comment_type import ReplyCommentType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_comment_object import DesignCommentObject
    from ..models.reply_comment_mentions import ReplyCommentMentions
    from ..models.user import User


T = TypeVar("T", bound="ReplyComment")


@_attrs_define
class ReplyComment:
    """Data about the reply comment, including the message, author, and
    the object (such as a design) the comment is attached to.

        Attributes:
            type_ (ReplyCommentType):
            id (str): The ID of the comment. Example: KeAZEAjijEb.
            message (str): The comment message. This is the comment body shown in the Canva UI.
                User mentions are shown here in the format `[user_id:team_id]`. Example: Thanks!.
            author (User): Metadata for the user, consisting of the User ID and display name.
            mentions (ReplyCommentMentions): The Canva users mentioned in the comment. Example:
                {'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP': {'user_id': 'oUnPjZ2k2yuhftbWF7873o', 'team_id':
                'oBpVhLW22VrqtwKgaayRbP', 'display_name': 'John Doe'}}.
            thread_id (str): The ID of the comment thread this reply is in. This ID is the same as the `id` of the
                parent comment. Example: KeAbiEAjZEj.
            attached_to (DesignCommentObject | Unset): If the comment is attached to a Canva Design.
            created_at (int | Unset): When the comment or reply was created, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692929800.
            updated_at (int | Unset): When the comment or reply was last updated, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692929900.
    """

    type_: ReplyCommentType
    id: str
    message: str
    author: User
    mentions: ReplyCommentMentions
    thread_id: str
    attached_to: DesignCommentObject | Unset = UNSET
    created_at: int | Unset = UNSET
    updated_at: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = self.id

        message = self.message

        author = self.author.to_dict()

        mentions = self.mentions.to_dict()

        thread_id = self.thread_id

        attached_to: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attached_to, Unset):
            attached_to = self.attached_to.to_dict()

        created_at = self.created_at

        updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "id": id,
                "message": message,
                "author": author,
                "mentions": mentions,
                "thread_id": thread_id,
            }
        )
        if attached_to is not UNSET:
            field_dict["attached_to"] = attached_to
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_comment_object import DesignCommentObject
        from ..models.reply_comment_mentions import ReplyCommentMentions
        from ..models.user import User

        d = dict(src_dict)
        type_ = ReplyCommentType(d.pop("type"))

        id = d.pop("id")

        message = d.pop("message")

        author = User.from_dict(d.pop("author"))

        mentions = ReplyCommentMentions.from_dict(d.pop("mentions"))

        thread_id = d.pop("thread_id")

        _attached_to = d.pop("attached_to", UNSET)
        attached_to: DesignCommentObject | Unset
        if isinstance(_attached_to, Unset):
            attached_to = UNSET
        else:
            attached_to = DesignCommentObject.from_dict(_attached_to)

        created_at = d.pop("created_at", UNSET)

        updated_at = d.pop("updated_at", UNSET)

        reply_comment = cls(
            type_=type_,
            id=id,
            message=message,
            author=author,
            mentions=mentions,
            thread_id=thread_id,
            attached_to=attached_to,
            created_at=created_at,
            updated_at=updated_at,
        )

        reply_comment.additional_properties = d
        return reply_comment

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
