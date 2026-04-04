from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.comment_content import CommentContent
    from ..models.reply_mentions import ReplyMentions
    from ..models.user import User


T = TypeVar("T", bound="Reply")


@_attrs_define
class Reply:
    """A reply to a thread.

    The `author` of the reply might be missing if that user account no longer exists.

        Attributes:
            id (str): The ID of the reply. Example: KeAZEAjijEb.
            design_id (str): The ID of the design that the thread for this reply is attached to. Example: DAFVztcvd9z.
            thread_id (str): The ID of the thread this reply is in. Example: KeAbiEAjZEj.
            content (CommentContent): The content of a comment thread or reply.
            mentions (ReplyMentions): The Canva users mentioned in the comment thread or reply. Example:
                {'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP': {'tag': 'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP',
                'user': {'user_id': 'oUnPjZ2k2yuhftbWF7873o', 'team_id': 'oBpVhLW22VrqtwKgaayRbP', 'display_name': 'John
                Doe'}}}.
            created_at (int): When the reply was created, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692929800.
            updated_at (int): When the reply was last updated, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692929900.
            author (User | Unset): Metadata for the user, consisting of the User ID and display name.
    """

    id: str
    design_id: str
    thread_id: str
    content: CommentContent
    mentions: ReplyMentions
    created_at: int
    updated_at: int
    author: User | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        design_id = self.design_id

        thread_id = self.thread_id

        content = self.content.to_dict()

        mentions = self.mentions.to_dict()

        created_at = self.created_at

        updated_at = self.updated_at

        author: dict[str, Any] | Unset = UNSET
        if not isinstance(self.author, Unset):
            author = self.author.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "design_id": design_id,
                "thread_id": thread_id,
                "content": content,
                "mentions": mentions,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if author is not UNSET:
            field_dict["author"] = author

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.comment_content import CommentContent
        from ..models.reply_mentions import ReplyMentions
        from ..models.user import User

        d = dict(src_dict)
        id = d.pop("id")

        design_id = d.pop("design_id")

        thread_id = d.pop("thread_id")

        content = CommentContent.from_dict(d.pop("content"))

        mentions = ReplyMentions.from_dict(d.pop("mentions"))

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        _author = d.pop("author", UNSET)
        author: User | Unset
        if isinstance(_author, Unset):
            author = UNSET
        else:
            author = User.from_dict(_author)

        reply = cls(
            id=id,
            design_id=design_id,
            thread_id=thread_id,
            content=content,
            mentions=mentions,
            created_at=created_at,
            updated_at=updated_at,
            author=author,
        )

        reply.additional_properties = d
        return reply

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
