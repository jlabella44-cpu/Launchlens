from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="MoveFolderItemRequest")


@_attrs_define
class MoveFolderItemRequest:
    """Body parameters for moving the folder.

    Attributes:
        to_folder_id (str): The ID of the folder you want to move the item to (the destination folder).
            If you want to move the item to the top level of a Canva user's
            [projects](https://www.canva.com/help/find-designs-and-folders/), use the ID `root`. Example: FAF2lZtloor.
        item_id (str): The ID of the item you want to move. Currently, video assets are not supported. Example:
            Msd59349ff.
    """

    to_folder_id: str
    item_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        to_folder_id = self.to_folder_id

        item_id = self.item_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "to_folder_id": to_folder_id,
                "item_id": item_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        to_folder_id = d.pop("to_folder_id")

        item_id = d.pop("item_id")

        move_folder_item_request = cls(
            to_folder_id=to_folder_id,
            item_id=item_id,
        )

        move_folder_item_request.additional_properties = d
        return move_folder_item_request

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
