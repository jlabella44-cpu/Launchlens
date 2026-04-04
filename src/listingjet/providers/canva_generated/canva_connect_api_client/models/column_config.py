from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.column_data_type import ColumnDataType
from ..types import UNSET, Unset

T = TypeVar("T", bound="ColumnConfig")


@_attrs_define
class ColumnConfig:
    """Configuration for a data table column.

    Attributes:
        type_ (ColumnDataType): Expected data type for cells in this column.
        name (str | Unset): Name for the column, displayed as header text.
    """

    type_: ColumnDataType
    name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = ColumnDataType(d.pop("type"))

        name = d.pop("name", UNSET)

        column_config = cls(
            type_=type_,
            name=name,
        )

        column_config.additional_properties = d
        return column_config

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
