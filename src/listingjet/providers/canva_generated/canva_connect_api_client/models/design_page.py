from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.page_dimensions import PageDimensions
    from ..models.thumbnail import Thumbnail


T = TypeVar("T", bound="DesignPage")


@_attrs_define
class DesignPage:
    """Basic details about a page in a design, such as the page's index and thumbnail.

    Attributes:
        index (int): The index of the page in the design. The first page in a design has the index value `1`.
        dimensions (PageDimensions | Unset): The dimensions of a design page, if it is bounded. Design pages for non-
            bounded designs like Whiteboards and Docs will not include this property.
        thumbnail (Thumbnail | Unset): A thumbnail image representing the object.
    """

    index: int
    dimensions: PageDimensions | Unset = UNSET
    thumbnail: Thumbnail | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        index = self.index

        dimensions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.dimensions, Unset):
            dimensions = self.dimensions.to_dict()

        thumbnail: dict[str, Any] | Unset = UNSET
        if not isinstance(self.thumbnail, Unset):
            thumbnail = self.thumbnail.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "index": index,
            }
        )
        if dimensions is not UNSET:
            field_dict["dimensions"] = dimensions
        if thumbnail is not UNSET:
            field_dict["thumbnail"] = thumbnail

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.page_dimensions import PageDimensions
        from ..models.thumbnail import Thumbnail

        d = dict(src_dict)
        index = d.pop("index")

        _dimensions = d.pop("dimensions", UNSET)
        dimensions: PageDimensions | Unset
        if isinstance(_dimensions, Unset):
            dimensions = UNSET
        else:
            dimensions = PageDimensions.from_dict(_dimensions)

        _thumbnail = d.pop("thumbnail", UNSET)
        thumbnail: Thumbnail | Unset
        if isinstance(_thumbnail, Unset):
            thumbnail = UNSET
        else:
            thumbnail = Thumbnail.from_dict(_thumbnail)

        design_page = cls(
            index=index,
            dimensions=dimensions,
            thumbnail=thumbnail,
        )

        design_page.additional_properties = d
        return design_page

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
