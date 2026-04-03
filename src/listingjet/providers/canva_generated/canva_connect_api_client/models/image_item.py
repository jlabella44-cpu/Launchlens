from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.image_item_type import ImageItemType

if TYPE_CHECKING:
    from ..models.asset_summary import AssetSummary


T = TypeVar("T", bound="ImageItem")


@_attrs_define
class ImageItem:
    """Details about the image asset.

    Attributes:
        type_ (ImageItemType):
        image (AssetSummary): An object representing an asset with associated metadata.
    """

    type_: ImageItemType
    image: AssetSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        image = self.image.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "image": image,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.asset_summary import AssetSummary

        d = dict(src_dict)
        type_ = ImageItemType(d.pop("type"))

        image = AssetSummary.from_dict(d.pop("image"))

        image_item = cls(
            type_=type_,
            image=image,
        )

        image_item.additional_properties = d
        return image_item

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
