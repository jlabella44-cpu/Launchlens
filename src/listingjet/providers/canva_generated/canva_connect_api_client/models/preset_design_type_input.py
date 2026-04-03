from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.preset_design_type_input_type import PresetDesignTypeInputType
from ..models.preset_design_type_name import PresetDesignTypeName

T = TypeVar("T", bound="PresetDesignTypeInput")


@_attrs_define
class PresetDesignTypeInput:
    """Provide the common design type.

    Attributes:
        type_ (PresetDesignTypeInputType):
        name (PresetDesignTypeName): The name of the design type.
    """

    type_: PresetDesignTypeInputType
    name: PresetDesignTypeName
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        name = self.name.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "name": name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = PresetDesignTypeInputType(d.pop("type"))

        name = PresetDesignTypeName(d.pop("name"))

        preset_design_type_input = cls(
            type_=type_,
            name=name,
        )

        preset_design_type_input.additional_properties = d
        return preset_design_type_input

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
