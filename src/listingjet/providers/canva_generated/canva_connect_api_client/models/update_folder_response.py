from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.folder import Folder


T = TypeVar("T", bound="UpdateFolderResponse")


@_attrs_define
class UpdateFolderResponse:
    """Details about the updated folder.

    Attributes:
        folder (Folder | Unset): The folder object, which contains metadata about the folder.
    """

    folder: Folder | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        folder: dict[str, Any] | Unset = UNSET
        if not isinstance(self.folder, Unset):
            folder = self.folder.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if folder is not UNSET:
            field_dict["folder"] = folder

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.folder import Folder

        d = dict(src_dict)
        _folder = d.pop("folder", UNSET)
        folder: Folder | Unset
        if isinstance(_folder, Unset):
            folder = UNSET
        else:
            folder = Folder.from_dict(_folder)

        update_folder_response = cls(
            folder=folder,
        )

        update_folder_response.additional_properties = d
        return update_folder_response

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
