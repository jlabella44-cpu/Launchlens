from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.dataset_chart_value import DatasetChartValue
    from ..models.dataset_image_value import DatasetImageValue
    from ..models.dataset_text_value import DatasetTextValue


T = TypeVar("T", bound="CreateDesignAutofillJobRequestData")


@_attrs_define
class CreateDesignAutofillJobRequestData:
    """Data object containing the data fields and values to autofill.

    Example:
        {'cute_pet_image_of_the_day': {'type': 'image', 'asset_id': 'Msd59349ff'}, 'cute_pet_witty_pet_says': {'type':
            'text', 'text': 'It was like this when I got here!'}, 'cute_pet_sales_chart': {'type': 'chart', 'chart_data':
            {'column_configs': [{'name': 'Geographic Region', 'type': 'string'}, {'name': 'Sales (millions AUD)', 'type':
            'number'}, {'name': 'Target (millions AUD)', 'type': 'number'}, {'name': 'Target met?', 'type': 'boolean'},
            {'name': 'Date met', 'type': 'date'}], 'rows': [{'cells': [{'type': 'string', 'value': 'Asia Pacific'}, {'type':
            'number', 'value': 10.2}, {'type': 'number', 'value': 10}, {'type': 'boolean', 'value': True}, {'type': 'date',
            'value': 1721944387}]}, {'cells': [{'type': 'string', 'value': 'EMEA'}, {'type': 'number', 'value': 13.8},
            {'type': 'number', 'value': 14}, {'type': 'boolean', 'value': False}, {'type': 'date'}]}]}}}

    """

    additional_properties: dict[str, DatasetChartValue | DatasetImageValue | DatasetTextValue] = _attrs_field(
        init=False, factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        from ..models.dataset_image_value import DatasetImageValue
        from ..models.dataset_text_value import DatasetTextValue

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            if isinstance(prop, DatasetImageValue):
                field_dict[prop_name] = prop.to_dict()
            elif isinstance(prop, DatasetTextValue):
                field_dict[prop_name] = prop.to_dict()
            else:
                field_dict[prop_name] = prop.to_dict()

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dataset_chart_value import DatasetChartValue
        from ..models.dataset_image_value import DatasetImageValue
        from ..models.dataset_text_value import DatasetTextValue

        d = dict(src_dict)
        create_design_autofill_job_request_data = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():

            def _parse_additional_property(data: object) -> DatasetChartValue | DatasetImageValue | DatasetTextValue:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_dataset_value_type_0 = DatasetImageValue.from_dict(data)

                    return componentsschemas_dataset_value_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_dataset_value_type_1 = DatasetTextValue.from_dict(data)

                    return componentsschemas_dataset_value_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_dataset_value_type_2 = DatasetChartValue.from_dict(data)

                return componentsschemas_dataset_value_type_2

            additional_property = _parse_additional_property(prop_dict)

            additional_properties[prop_name] = additional_property

        create_design_autofill_job_request_data.additional_properties = additional_properties
        return create_design_autofill_job_request_data

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> DatasetChartValue | DatasetImageValue | DatasetTextValue:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: DatasetChartValue | DatasetImageValue | DatasetTextValue) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
