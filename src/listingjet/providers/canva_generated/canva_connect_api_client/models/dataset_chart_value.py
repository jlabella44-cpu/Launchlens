from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.dataset_chart_value_type import DatasetChartValueType

if TYPE_CHECKING:
    from ..models.data_table import DataTable


T = TypeVar("T", bound="DatasetChartValue")


@_attrs_define
class DatasetChartValue:
    """If the data field is a chart.

    Note the following behavior:
    - If `column_configs` is not provided, the first row is assumed to contain column headers where applicable.
    - `number` cells with formatting metadata are not currently supported for autofill and will result in an error
    response.
    - `media` cells are not supported for chart autofill and will result in an error response.

     WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-apis). There might
    be unannounced breaking changes to this feature which won't produce a new API version.

        Attributes:
            type_ (DatasetChartValueType):
            chart_data (DataTable): Tabular data, structured in rows of cells.

                - Each cell must have a data type configured.
                - All rows must have the same number of cells.
                - The number of entries in `column_configs` must match the number of columns in the data.
                - Maximum of 100 rows and 20 columns.

                WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-apis). There
                might be unannounced breaking changes to this feature which won't produce a new API version. Example:
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
                {'type': 'date'}, {'type': 'media', 'value': []}]}]}.
    """

    type_: DatasetChartValueType
    chart_data: DataTable
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        chart_data = self.chart_data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "chart_data": chart_data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.data_table import DataTable

        d = dict(src_dict)
        type_ = DatasetChartValueType(d.pop("type"))

        chart_data = DataTable.from_dict(d.pop("chart_data"))

        dataset_chart_value = cls(
            type_=type_,
            chart_data=chart_data,
        )

        dataset_chart_value.additional_properties = d
        return dataset_chart_value

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
