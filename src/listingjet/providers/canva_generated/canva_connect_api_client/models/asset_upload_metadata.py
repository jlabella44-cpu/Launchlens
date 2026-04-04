from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="AssetUploadMetadata")


@_attrs_define
class AssetUploadMetadata:
    """Metadata for the asset being uploaded.

    Attributes:
        name_base64 (str): The asset's name, encoded in Base64.

            The maximum length of an asset name in Canva (unencoded) is 50 characters.

            Base64 encoding allows names containing emojis and other special
            characters to be sent using HTTP headers.
            For example, "My Awesome Upload 🚀" Base64 encoded
            is `TXkgQXdlc29tZSBVcGxvYWQg8J+agA==`. Example: TXkgQXdlc29tZSBVcGxvYWQg8J+agA==.
    """

    name_base64: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name_base64 = self.name_base64

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name_base64": name_base64,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name_base64 = d.pop("name_base64")

        asset_upload_metadata = cls(
            name_base64=name_base64,
        )

        asset_upload_metadata.additional_properties = d
        return asset_upload_metadata

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
