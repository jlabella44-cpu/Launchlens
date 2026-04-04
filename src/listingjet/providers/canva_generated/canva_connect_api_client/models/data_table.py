from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.column_config import ColumnConfig
    from ..models.data_table_row import DataTableRow


T = TypeVar("T", bound="DataTable")


@_attrs_define
class DataTable:
    """Tabular data, structured in rows of cells.

    - Each cell must have a data type configured.
    - All rows must have the same number of cells.
    - The number of entries in `column_configs` must match the number of columns in the data.
    - Maximum of 100 rows and 20 columns.

    WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-apis). There might be
    unannounced breaking changes to this feature which won't produce a new API version.

        Example:
            {'column_configs': [{'name': 'Geographic Region', 'type': 'string'}, {'name': 'Sales (millions AUD)', 'type':
                'number'}, {'name': 'Target (millions AUD)', 'type': 'number'}, {'name': 'Target met?', 'type': 'boolean'},
                {'name': 'Date met', 'type': 'date'}, {'name': 'Logo', 'type': 'media'}], 'rows': [{'cells': [{'type': 'string',
                'value': 'Asia Pacific'}, {'type': 'number', 'value': 10.2, 'metadata': {'formatting': '#,##0.0'}}, {'type':
                'number', 'value': 10, 'metadata': {'formatting': '#,##0.0'}}, {'type': 'boolean', 'value': True}, {'type':
                'date', 'value': 1721944387}, {'type': 'media', 'value': [{'type': 'image_upload', 'url':
                'https://example.com/apac-logo.png', 'thumbnail_url': 'https://example.com/apac-logo-thumb.png', 'mime_type':
                'image/png', 'ai_disclosure': 'none'}, {'type': 'video_upload', 'url': 'https://example.com/apac-logo.mp4',
                'thumbnail_image_url': 'https://example.com/apac-logo-thumb.png', 'thumbnail_video_url':
                'https://example.com/apac-logo-thumb.mp4', 'mime_type': 'video/mp4', 'ai_disclosure': 'none'}]}]}, {'cells':
                [{'type': 'string', 'value': 'EMEA'}, {'type': 'number', 'value': 13.8, 'metadata': {'formatting': '#,##0.0'}},
                {'type': 'number', 'value': 14, 'metadata': {'formatting': '#,##0.0'}}, {'type': 'boolean', 'value': False},
                {'type': 'date'}, {'type': 'media', 'value': []}]}]}

        Attributes:
            rows (list[DataTableRow]): Rows of data.
            column_configs (list[ColumnConfig] | Unset): Column definitions with names and data types.
    """

    rows: list[DataTableRow]
    column_configs: list[ColumnConfig] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        rows = []
        for rows_item_data in self.rows:
            rows_item = rows_item_data.to_dict()
            rows.append(rows_item)

        column_configs: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.column_configs, Unset):
            column_configs = []
            for column_configs_item_data in self.column_configs:
                column_configs_item = column_configs_item_data.to_dict()
                column_configs.append(column_configs_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "rows": rows,
            }
        )
        if column_configs is not UNSET:
            field_dict["column_configs"] = column_configs

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.column_config import ColumnConfig
        from ..models.data_table_row import DataTableRow

        d = dict(src_dict)
        rows = []
        _rows = d.pop("rows")
        for rows_item_data in _rows:
            rows_item = DataTableRow.from_dict(rows_item_data)

            rows.append(rows_item)

        _column_configs = d.pop("column_configs", UNSET)
        column_configs: list[ColumnConfig] | Unset = UNSET
        if _column_configs is not UNSET:
            column_configs = []
            for column_configs_item_data in _column_configs:
                column_configs_item = ColumnConfig.from_dict(column_configs_item_data)

                column_configs.append(column_configs_item)

        data_table = cls(
            rows=rows,
            column_configs=column_configs,
        )

        data_table.additional_properties = d
        return data_table

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
