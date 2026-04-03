from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.asset_upload_error_code import AssetUploadErrorCode

T = TypeVar("T", bound="AssetUploadError")


@_attrs_define
class AssetUploadError:
    """If the upload fails, this object provides details about the error.

    Attributes:
        code (AssetUploadErrorCode): A short string indicating why the upload failed. This field can be used to handle
            errors
            programmatically. Example: file_too_big.
        message (str): A human-readable description of what went wrong. Example: Failed to import because the file is
            too big..
    """

    code: AssetUploadErrorCode
    message: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        code = self.code.value

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "code": code,
                "message": message,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        code = AssetUploadErrorCode(d.pop("code"))

        message = d.pop("message")

        asset_upload_error = cls(
            code=code,
            message=message,
        )

        asset_upload_error.additional_properties = d
        return asset_upload_error

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
