from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DesignImportMetadata")


@_attrs_define
class DesignImportMetadata:
    """Metadata about the design that you include as a header parameter when importing a design.

    Attributes:
        title_base64 (str): The design's title, encoded in Base64.

            The maximum length of a design title in Canva (unencoded) is 50 characters.

            Base64 encoding allows titles containing emojis and other special
            characters to be sent using HTTP headers.
            For example, "My Awesome Design 😍" Base64 encoded
            is `TXkgQXdlc29tZSBEZXNpZ24g8J+YjQ==`. Example: TXkgQXdlc29tZSBEZXNpZ24g8J+YjQ==.
        mime_type (str | Unset): The MIME type of the file being imported. If not provided, Canva attempts to
            automatically detect the type of the file. Example: application/pdf.
    """

    title_base64: str
    mime_type: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title_base64 = self.title_base64

        mime_type = self.mime_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title_base64": title_base64,
            }
        )
        if mime_type is not UNSET:
            field_dict["mime_type"] = mime_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title_base64 = d.pop("title_base64")

        mime_type = d.pop("mime_type", UNSET)

        design_import_metadata = cls(
            title_base64=title_base64,
            mime_type=mime_type,
        )

        design_import_metadata.additional_properties = d
        return design_import_metadata

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
