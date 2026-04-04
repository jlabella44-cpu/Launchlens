from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.parent_comment import ParentComment


T = TypeVar("T", bound="CreateCommentResponse")


@_attrs_define
class CreateCommentResponse:
    """
    Attributes:
        comment (ParentComment): Data about the comment, including the message, author, and
            the object (such as a design) the comment is attached to.
    """

    comment: ParentComment
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        comment = self.comment.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "comment": comment,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.parent_comment import ParentComment

        d = dict(src_dict)
        comment = ParentComment.from_dict(d.pop("comment"))

        create_comment_response = cls(
            comment=comment,
        )

        create_comment_response.additional_properties = d
        return create_comment_response

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
