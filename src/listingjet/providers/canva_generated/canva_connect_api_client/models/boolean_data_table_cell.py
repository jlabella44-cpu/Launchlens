from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.boolean_data_table_cell_type import BooleanDataTableCellType
from ..types import UNSET, Unset

T = TypeVar("T", bound="BooleanDataTableCell")


@_attrs_define
class BooleanDataTableCell:
    """A boolean tabular data cell.

    Attributes:
        type_ (BooleanDataTableCellType):
        value (bool | Unset):
    """

    type_: BooleanDataTableCellType
    value: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = BooleanDataTableCellType(d.pop("type"))

        value = d.pop("value", UNSET)

        boolean_data_table_cell = cls(
            type_=type_,
            value=value,
        )

        boolean_data_table_cell.additional_properties = d
        return boolean_data_table_cell

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
