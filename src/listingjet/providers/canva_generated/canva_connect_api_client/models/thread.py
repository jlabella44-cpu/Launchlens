from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.comment_thread_type import CommentThreadType
    from ..models.suggestion_thread_type import SuggestionThreadType
    from ..models.user import User


T = TypeVar("T", bound="Thread")


@_attrs_define
class Thread:
    """A discussion thread on a design.

    The `type` of the thread can be found in the `thread_type` object, along with additional type-specific properties.
    The `author` of the thread might be missing if that user account no longer exists.

        Attributes:
            id (str): The ID of the thread.

                You can use this ID to create replies to the thread using the [Create reply
                API](https://www.canva.dev/docs/connect/api-reference/comments/create-reply/). Example: KeAbiEAjZEj.
            design_id (str): The ID of the design that the discussion thread is on. Example: DAFVztcvd9z.
            thread_type (CommentThreadType | SuggestionThreadType): The type of the discussion thread, along with additional
                type-specific properties.
            created_at (int): When the thread was created, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692928800.
            updated_at (int): When the thread was last updated, as a Unix timestamp
                (in seconds since the Unix Epoch). Example: 1692928900.
            author (User | Unset): Metadata for the user, consisting of the User ID and display name.
    """

    id: str
    design_id: str
    thread_type: CommentThreadType | SuggestionThreadType
    created_at: int
    updated_at: int
    author: User | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.comment_thread_type import CommentThreadType

        id = self.id

        design_id = self.design_id

        thread_type: dict[str, Any]
        if isinstance(self.thread_type, CommentThreadType):
            thread_type = self.thread_type.to_dict()
        else:
            thread_type = self.thread_type.to_dict()

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
                "thread_type": thread_type,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if author is not UNSET:
            field_dict["author"] = author

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.comment_thread_type import CommentThreadType
        from ..models.suggestion_thread_type import SuggestionThreadType
        from ..models.user import User

        d = dict(src_dict)
        id = d.pop("id")

        design_id = d.pop("design_id")

        def _parse_thread_type(data: object) -> CommentThreadType | SuggestionThreadType:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_thread_type_type_0 = CommentThreadType.from_dict(data)

                return componentsschemas_thread_type_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_thread_type_type_1 = SuggestionThreadType.from_dict(data)

            return componentsschemas_thread_type_type_1

        thread_type = _parse_thread_type(d.pop("thread_type"))

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        _author = d.pop("author", UNSET)
        author: User | Unset
        if isinstance(_author, Unset):
            author = UNSET
        else:
            author = User.from_dict(_author)

        thread = cls(
            id=id,
            design_id=design_id,
            thread_type=thread_type,
            created_at=created_at,
            updated_at=updated_at,
            author=author,
        )

        thread.additional_properties = d
        return thread

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
