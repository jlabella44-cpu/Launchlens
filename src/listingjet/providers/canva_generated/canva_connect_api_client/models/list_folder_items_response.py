from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_item import DesignItem
    from ..models.folder_item import FolderItem
    from ..models.image_item import ImageItem


T = TypeVar("T", bound="ListFolderItemsResponse")


@_attrs_define
class ListFolderItemsResponse:
    """A list of the items in a folder.
    If the success response contains a continuation token, the folder contains more items
    you can list. You can use this token as a query parameter and retrieve more
    items from the list, for example
    `/v1/folders/{folderId}/items?continuation={continuation}`.

    To retrieve all the items in a folder, you might need to make multiple requests.

        Attributes:
            items (list[DesignItem | FolderItem | ImageItem]): An array of items in the folder.
            continuation (str | Unset): If the success response contains a continuation token, the folder contains more
                items
                you can list. You can use this token as a query parameter and retrieve more
                items from the list, for example
                `/v1/folders/{folderId}/items?continuation={continuation}`.

                To retrieve all the items in a folder, you might need to make multiple requests. Example:
                RkFGMgXlsVTDbMd:MR3L0QjiaUzycIAjx0yMyuNiV0OildoiOwL0x32G4NjNu4FwtAQNxowUQNMMYN.
    """

    items: list[DesignItem | FolderItem | ImageItem]
    continuation: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.design_item import DesignItem
        from ..models.folder_item import FolderItem

        items = []
        for items_item_data in self.items:
            items_item: dict[str, Any]
            if isinstance(items_item_data, FolderItem):
                items_item = items_item_data.to_dict()
            elif isinstance(items_item_data, DesignItem):
                items_item = items_item_data.to_dict()
            else:
                items_item = items_item_data.to_dict()

            items.append(items_item)

        continuation = self.continuation

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
            }
        )
        if continuation is not UNSET:
            field_dict["continuation"] = continuation

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_item import DesignItem
        from ..models.folder_item import FolderItem
        from ..models.image_item import ImageItem

        d = dict(src_dict)
        items = []
        _items = d.pop("items")
        for items_item_data in _items:

            def _parse_items_item(data: object) -> DesignItem | FolderItem | ImageItem:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_folder_item_summary_type_0 = FolderItem.from_dict(data)

                    return componentsschemas_folder_item_summary_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_folder_item_summary_type_1 = DesignItem.from_dict(data)

                    return componentsschemas_folder_item_summary_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_folder_item_summary_type_2 = ImageItem.from_dict(data)

                return componentsschemas_folder_item_summary_type_2

            items_item = _parse_items_item(items_item_data)

            items.append(items_item)

        continuation = d.pop("continuation", UNSET)

        list_folder_items_response = cls(
            items=items,
            continuation=continuation,
        )

        list_folder_items_response.additional_properties = d
        return list_folder_items_response

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
