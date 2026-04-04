from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.custom_design_type_input_type import CustomDesignTypeInputType

T = TypeVar("T", bound="CustomDesignTypeInput")


@_attrs_define
class CustomDesignTypeInput:
    """Provide the width and height to define a custom design type.

    Attributes:
        type_ (CustomDesignTypeInputType):
        width (int): The width of the design, in pixels. Example: 320.
        height (int): The height of the design, in pixels. Example: 200.
    """

    type_: CustomDesignTypeInputType
    width: int
    height: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        width = self.width

        height = self.height

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "width": width,
                "height": height,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = CustomDesignTypeInputType(d.pop("type"))

        width = d.pop("width")

        height = d.pop("height")

        custom_design_type_input = cls(
            type_=type_,
            width=width,
            height=height,
        )

        custom_design_type_input.additional_properties = d
        return custom_design_type_input

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
