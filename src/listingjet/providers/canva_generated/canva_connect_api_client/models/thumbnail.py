from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Thumbnail")


@_attrs_define
class Thumbnail:
    """A thumbnail image representing the object.

    Attributes:
        width (int): The width of the thumbnail image in pixels. Example: 595.
        height (int): The height of the thumbnail image in pixels. Example: 335.
        url (str): A URL for retrieving the thumbnail image.
            This URL expires after 15 minutes. This URL includes a query string
            that's required for retrieving the thumbnail. Example: https://document-
            export.canva.com/Vczz9/zF9vzVtdADc/2/thumbnail/0001.png?<query-string>.
    """

    width: int
    height: int
    url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        width = self.width

        height = self.height

        url = self.url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "width": width,
                "height": height,
                "url": url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        width = d.pop("width")

        height = d.pop("height")

        url = d.pop("url")

        thumbnail = cls(
            width=width,
            height=height,
            url=url,
        )

        thumbnail.additional_properties = d
        return thumbnail

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
