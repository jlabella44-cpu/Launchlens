from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.reply import Reply


T = TypeVar("T", bound="ListRepliesResponse")


@_attrs_define
class ListRepliesResponse:
    """Successful response from a `listReplies` request.

    Attributes:
        items (list[Reply]):
        continuation (str | Unset): If the success response contains a continuation token, the list contains more items
            you can list. You can use this token as a query parameter and retrieve more items
            from the list, for example `?continuation={continuation}`.

            To retrieve all items, you might need to make multiple requests. Example:
            RkFGMgXlsVTDbMd:MR3L0QjiaUzycIAjx0yMyuNiV0OildoiOwL0x32G4NjNu4FwtAQNxowUQNMMYN.
    """

    items: list[Reply]
    continuation: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        items = []
        for items_item_data in self.items:
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
        from ..models.reply import Reply

        d = dict(src_dict)
        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = Reply.from_dict(items_item_data)

            items.append(items_item)

        continuation = d.pop("continuation", UNSET)

        list_replies_response = cls(
            items=items,
            continuation=continuation,
        )

        list_replies_response.additional_properties = d
        return list_replies_response

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
