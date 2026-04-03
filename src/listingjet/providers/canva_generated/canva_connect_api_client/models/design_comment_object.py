from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_comment_object_type import DesignCommentObjectType

T = TypeVar("T", bound="DesignCommentObject")


@_attrs_define
class DesignCommentObject:
    """If the comment is attached to a Canva Design.

    Attributes:
        type_ (DesignCommentObjectType):
        design_id (str): The ID of the design this comment is attached to. Example: DAFVztcvd9z.
    """

    type_: DesignCommentObjectType
    design_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        design_id = self.design_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "design_id": design_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = DesignCommentObjectType(d.pop("type"))

        design_id = d.pop("design_id")

        design_comment_object = cls(
            type_=type_,
            design_id=design_id,
        )

        design_comment_object.additional_properties = d
        return design_comment_object

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
