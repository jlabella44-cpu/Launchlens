from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.capability import Capability
from ..types import UNSET, Unset

T = TypeVar("T", bound="GetUserCapabilitiesResponse")


@_attrs_define
class GetUserCapabilitiesResponse:
    """
    Attributes:
        capabilities (list[Capability] | Unset):
    """

    capabilities: list[Capability] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        capabilities: list[str] | Unset = UNSET
        if not isinstance(self.capabilities, Unset):
            capabilities = []
            for capabilities_item_data in self.capabilities:
                capabilities_item = capabilities_item_data.value
                capabilities.append(capabilities_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if capabilities is not UNSET:
            field_dict["capabilities"] = capabilities

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _capabilities = d.pop("capabilities", UNSET)
        capabilities: list[Capability] | Unset = UNSET
        if _capabilities is not UNSET:
            capabilities = []
            for capabilities_item_data in _capabilities:
                capabilities_item = Capability(capabilities_item_data)

                capabilities.append(capabilities_item)

        get_user_capabilities_response = cls(
            capabilities=capabilities,
        )

        get_user_capabilities_response.additional_properties = d
        return get_user_capabilities_response

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
