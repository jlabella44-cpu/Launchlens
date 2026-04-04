from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PageDimensions")


@_attrs_define
class PageDimensions:
    """The dimensions of a design page, if it is bounded. Design pages for non-bounded designs like Whiteboards and Docs
    will not include this property.

        Attributes:
            width (float): The width of the design page in pixels. Example: 595.
            height (float): The height of the design page in pixels. Example: 1295.
    """

    width: float
    height: float
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        width = self.width

        height = self.height

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "width": width,
                "height": height,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        width = d.pop("width")

        height = d.pop("height")

        page_dimensions = cls(
            width=width,
            height=height,
        )

        page_dimensions.additional_properties = d
        return page_dimensions

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
