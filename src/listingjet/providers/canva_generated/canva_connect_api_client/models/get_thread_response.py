from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.parent_comment import ParentComment
    from ..models.reply_comment import ReplyComment
    from ..models.thread import Thread


T = TypeVar("T", bound="GetThreadResponse")


@_attrs_define
class GetThreadResponse:
    """Successful response from a `getThread` request.

    The `comment` property is deprecated.
    For details of a comment thread, please use the `thread` property.

        Attributes:
            comment (ParentComment | ReplyComment | Unset): The comment object, which contains metadata about the comment.
                Deprecated in favor of the new `thread` object.
            thread (Thread | Unset): A discussion thread on a design.

                The `type` of the thread can be found in the `thread_type` object, along with additional type-specific
                properties.
                The `author` of the thread might be missing if that user account no longer exists.
    """

    comment: ParentComment | ReplyComment | Unset = UNSET
    thread: Thread | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.parent_comment import ParentComment

        comment: dict[str, Any] | Unset
        if isinstance(self.comment, Unset):
            comment = UNSET
        elif isinstance(self.comment, ParentComment):
            comment = self.comment.to_dict()
        else:
            comment = self.comment.to_dict()

        thread: dict[str, Any] | Unset = UNSET
        if not isinstance(self.thread, Unset):
            thread = self.thread.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if comment is not UNSET:
            field_dict["comment"] = comment
        if thread is not UNSET:
            field_dict["thread"] = thread

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.parent_comment import ParentComment
        from ..models.reply_comment import ReplyComment
        from ..models.thread import Thread

        d = dict(src_dict)

        def _parse_comment(data: object) -> ParentComment | ReplyComment | Unset:
            if isinstance(data, Unset):
                return data
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

        comment = _parse_comment(d.pop("comment", UNSET))

        _thread = d.pop("thread", UNSET)
        thread: Thread | Unset
        if isinstance(_thread, Unset):
            thread = UNSET
        else:
            thread = Thread.from_dict(_thread)

        get_thread_response = cls(
            comment=comment,
            thread=thread,
        )

        get_thread_response.additional_properties = d
        return get_thread_response

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
