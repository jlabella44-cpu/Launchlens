from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateUrlImportJobRequest")


@_attrs_define
class CreateUrlImportJobRequest:
    """
    Attributes:
        title (str): A title for the design. Example: My Awesome Design.
        url (str): The URL of the file to import. This URL must be accessible from the internet and be publicly
            available.
        mime_type (str | Unset): The MIME type of the file being imported. If not provided, Canva attempts to
            automatically detect the type of the file. Example: application/vnd.apple.keynote.
    """

    title: str
    url: str
    mime_type: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        url = self.url

        mime_type = self.mime_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "url": url,
            }
        )
        if mime_type is not UNSET:
            field_dict["mime_type"] = mime_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title")

        url = d.pop("url")

        mime_type = d.pop("mime_type", UNSET)

        create_url_import_job_request = cls(
            title=title,
            url=url,
            mime_type=mime_type,
        )

        create_url_import_job_request.additional_properties = d
        return create_url_import_job_request

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
