from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.chart_data_field_type import ChartDataFieldType

T = TypeVar("T", bound="ChartDataField")


@_attrs_define
class ChartDataField:
    """Chart data for a brand template. You can autofill the brand template with tabular data.

    WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-apis). There might be
    unannounced breaking changes to this feature which won't produce a new API version.

        Attributes:
            type_ (ChartDataFieldType):
    """

    type_: ChartDataFieldType
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = ChartDataFieldType(d.pop("type"))

        chart_data_field = cls(
            type_=type_,
        )

        chart_data_field.additional_properties = d
        return chart_data_field

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
