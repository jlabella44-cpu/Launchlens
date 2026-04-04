from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="FolderSummary")


@_attrs_define
class FolderSummary:
    """This object contains some folder metadata. You can retrieve additional metadata
    using the folder ID and the `/v1/folders/{folderId}` endpoint.

        Attributes:
            id (str): The folder ID. Example: FAF2lZtloor.
            name (str): The folder name, as shown in the Canva UI. Example: My awesome holiday.
            created_at (int): When the folder was created, as a Unix timestamp (in seconds since the
                Unix Epoch). Example: 1377396000.
            updated_at (int): When the folder was last updated, as a Unix timestamp (in seconds since the
                Unix Epoch). Example: 1692928800.
            title (str | Unset): The folder name, as shown in the Canva UI. This property is deprecated, so you should
                use the `name` property instead. Example: My awesome holiday.
            url (str | Unset): The folder URL. Example: https://www.canva.com/folder/FAF2lZtloor.
    """

    id: str
    name: str
    created_at: int
    updated_at: int
    title: str | Unset = UNSET
    url: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        created_at = self.created_at

        updated_at = self.updated_at

        title = self.title

        url = self.url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if url is not UNSET:
            field_dict["url"] = url

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        title = d.pop("title", UNSET)

        url = d.pop("url", UNSET)

        folder_summary = cls(
            id=id,
            name=name,
            created_at=created_at,
            updated_at=updated_at,
            title=title,
            url=url,
        )

        folder_summary.additional_properties = d
        return folder_summary

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
