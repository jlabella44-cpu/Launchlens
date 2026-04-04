from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.image_metadata_type import ImageMetadataType
from ..types import UNSET, Unset

T = TypeVar("T", bound="ImageMetadata")


@_attrs_define
class ImageMetadata:
    """
    Attributes:
        type_ (ImageMetadataType):
        width (int | Unset): The width of the image in pixels. Example: 1920.
        height (int | Unset): The height of the image in pixels. Example: 1080.
        smart_tags (list[str] | Unset): AI-generated tags for the image. Example: ['landscape', 'sunset', 'mountains',
            'nature'].
    """

    type_: ImageMetadataType
    width: int | Unset = UNSET
    height: int | Unset = UNSET
    smart_tags: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        width = self.width

        height = self.height

        smart_tags: list[str] | Unset = UNSET
        if not isinstance(self.smart_tags, Unset):
            smart_tags = self.smart_tags

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if width is not UNSET:
            field_dict["width"] = width
        if height is not UNSET:
            field_dict["height"] = height
        if smart_tags is not UNSET:
            field_dict["smart_tags"] = smart_tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = ImageMetadataType(d.pop("type"))

        width = d.pop("width", UNSET)

        height = d.pop("height", UNSET)

        smart_tags = cast(list[str], d.pop("smart_tags", UNSET))

        image_metadata = cls(
            type_=type_,
            width=width,
            height=height,
            smart_tags=smart_tags,
        )

        image_metadata.additional_properties = d
        return image_metadata

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
