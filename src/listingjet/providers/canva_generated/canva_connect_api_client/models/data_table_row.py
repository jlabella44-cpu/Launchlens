from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.boolean_data_table_cell import BooleanDataTableCell
    from ..models.date_data_table_cell import DateDataTableCell
    from ..models.media_collection_data_table_cell import MediaCollectionDataTableCell
    from ..models.number_data_table_cell import NumberDataTableCell
    from ..models.string_data_table_cell import StringDataTableCell


T = TypeVar("T", bound="DataTableRow")


@_attrs_define
class DataTableRow:
    """A single row of tabular data.

    Attributes:
        cells (list[BooleanDataTableCell | DateDataTableCell | MediaCollectionDataTableCell | NumberDataTableCell |
            StringDataTableCell]): Cells of data in row.

            All rows must have the same number of cells.
    """

    cells: list[
        BooleanDataTableCell
        | DateDataTableCell
        | MediaCollectionDataTableCell
        | NumberDataTableCell
        | StringDataTableCell
    ]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.boolean_data_table_cell import BooleanDataTableCell
        from ..models.date_data_table_cell import DateDataTableCell
        from ..models.number_data_table_cell import NumberDataTableCell
        from ..models.string_data_table_cell import StringDataTableCell

        cells = []
        for cells_item_data in self.cells:
            cells_item: dict[str, Any]
            if isinstance(cells_item_data, StringDataTableCell):
                cells_item = cells_item_data.to_dict()
            elif isinstance(cells_item_data, NumberDataTableCell):
                cells_item = cells_item_data.to_dict()
            elif isinstance(cells_item_data, BooleanDataTableCell):
                cells_item = cells_item_data.to_dict()
            elif isinstance(cells_item_data, DateDataTableCell):
                cells_item = cells_item_data.to_dict()
            else:
                cells_item = cells_item_data.to_dict()

            cells.append(cells_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "cells": cells,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.boolean_data_table_cell import BooleanDataTableCell
        from ..models.date_data_table_cell import DateDataTableCell
        from ..models.media_collection_data_table_cell import MediaCollectionDataTableCell
        from ..models.number_data_table_cell import NumberDataTableCell
        from ..models.string_data_table_cell import StringDataTableCell

        d = dict(src_dict)
        cells = []
        _cells = d.pop("cells")
        for cells_item_data in _cells:

            def _parse_cells_item(
                data: object,
            ) -> (
                BooleanDataTableCell
                | DateDataTableCell
                | MediaCollectionDataTableCell
                | NumberDataTableCell
                | StringDataTableCell
            ):
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_table_cell_type_0 = StringDataTableCell.from_dict(data)

                    return componentsschemas_data_table_cell_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_table_cell_type_1 = NumberDataTableCell.from_dict(data)

                    return componentsschemas_data_table_cell_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_table_cell_type_2 = BooleanDataTableCell.from_dict(data)

                    return componentsschemas_data_table_cell_type_2
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_table_cell_type_3 = DateDataTableCell.from_dict(data)

                    return componentsschemas_data_table_cell_type_3
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_data_table_cell_type_4 = MediaCollectionDataTableCell.from_dict(data)

                return componentsschemas_data_table_cell_type_4

            cells_item = _parse_cells_item(cells_item_data)

            cells.append(cells_item)

        data_table_row = cls(
            cells=cells,
        )

        data_table_row.additional_properties = d
        return data_table_row

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
