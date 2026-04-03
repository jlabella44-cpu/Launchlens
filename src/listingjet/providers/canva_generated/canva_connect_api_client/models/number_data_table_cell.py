from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.number_data_table_cell_type import NumberDataTableCellType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.number_cell_metadata import NumberCellMetadata


T = TypeVar("T", bound="NumberDataTableCell")


@_attrs_define
class NumberDataTableCell:
    """A number tabular data cell.

    Attributes:
        type_ (NumberDataTableCellType):
        value (float | Unset):
        metadata (NumberCellMetadata | Unset): Formatting metadata for number cells.
    """

    type_: NumberDataTableCellType
    value: float | Unset = UNSET
    metadata: NumberCellMetadata | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        value = self.value

        metadata: dict[str, Any] | Unset = UNSET
        if not isinstance(self.metadata, Unset):
            metadata = self.metadata.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if value is not UNSET:
            field_dict["value"] = value
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.number_cell_metadata import NumberCellMetadata

        d = dict(src_dict)
        type_ = NumberDataTableCellType(d.pop("type"))

        value = d.pop("value", UNSET)

        _metadata = d.pop("metadata", UNSET)
        metadata: NumberCellMetadata | Unset
        if isinstance(_metadata, Unset):
            metadata = UNSET
        else:
            metadata = NumberCellMetadata.from_dict(_metadata)

        number_data_table_cell = cls(
            type_=type_,
            value=value,
            metadata=metadata,
        )

        number_data_table_cell.additional_properties = d
        return number_data_table_cell

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
