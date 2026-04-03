from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CreateFolderRequest")


@_attrs_define
class CreateFolderRequest:
    """Body parameters for creating a new folder.

    Attributes:
        name (str): The name of the folder. Example: My awesome holiday.
        parent_folder_id (str): The folder ID of the parent folder. To create a new folder at the top level of a user's
            [projects](https://www.canva.com/help/find-designs-and-folders/), use the ID `root`.
            To create it in their Uploads folder, use `uploads`. Example: FAF2lZtloor.
    """

    name: str
    parent_folder_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        parent_folder_id = self.parent_folder_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "parent_folder_id": parent_folder_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        parent_folder_id = d.pop("parent_folder_id")

        create_folder_request = cls(
            name=name,
            parent_folder_id=parent_folder_id,
        )

        create_folder_request.additional_properties = d
        return create_folder_request

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
