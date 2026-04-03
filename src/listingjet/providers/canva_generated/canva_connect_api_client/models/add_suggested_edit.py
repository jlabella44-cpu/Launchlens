from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.add_suggested_edit_type import AddSuggestedEditType

T = TypeVar("T", bound="AddSuggestedEdit")


@_attrs_define
class AddSuggestedEdit:
    """A suggestion to add some text.

    Attributes:
        type_ (AddSuggestedEditType):
        text (str):  Example: fantastic.
    """

    type_: AddSuggestedEditType
    text: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        text = self.text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "text": text,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = AddSuggestedEditType(d.pop("type"))

        text = d.pop("text")

        add_suggested_edit = cls(
            type_=type_,
            text=text,
        )

        add_suggested_edit.additional_properties = d
        return add_suggested_edit

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
