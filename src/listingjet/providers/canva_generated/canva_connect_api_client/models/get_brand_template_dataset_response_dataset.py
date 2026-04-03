from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.chart_data_field import ChartDataField
    from ..models.image_data_field import ImageDataField
    from ..models.text_data_field import TextDataField


T = TypeVar("T", bound="GetBrandTemplateDatasetResponseDataset")


@_attrs_define
class GetBrandTemplateDatasetResponseDataset:
    """The dataset definition for the brand template. The dataset definition contains the data inputs available for use
    with the
    [Create design autofill job API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-
    job/).

        Example:
            {'cute_pet_image_of_the_day': {'type': 'image'}, 'cute_pet_witty_pet_says': {'type': 'text'},
                'cute_pet_sales_chart': {'type': 'chart'}}

    """

    additional_properties: dict[str, ChartDataField | ImageDataField | TextDataField] = _attrs_field(
        init=False, factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        from ..models.image_data_field import ImageDataField
        from ..models.text_data_field import TextDataField

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            if isinstance(prop, ImageDataField):
                field_dict[prop_name] = prop.to_dict()
            elif isinstance(prop, TextDataField):
                field_dict[prop_name] = prop.to_dict()
            else:
                field_dict[prop_name] = prop.to_dict()

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.chart_data_field import ChartDataField
        from ..models.image_data_field import ImageDataField
        from ..models.text_data_field import TextDataField

        d = dict(src_dict)
        get_brand_template_dataset_response_dataset = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():

            def _parse_additional_property(data: object) -> ChartDataField | ImageDataField | TextDataField:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_field_type_0 = ImageDataField.from_dict(data)

                    return componentsschemas_data_field_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_field_type_1 = TextDataField.from_dict(data)

                    return componentsschemas_data_field_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_data_field_type_2 = ChartDataField.from_dict(data)

                return componentsschemas_data_field_type_2

            additional_property = _parse_additional_property(prop_dict)

            additional_properties[prop_name] = additional_property

        get_brand_template_dataset_response_dataset.additional_properties = additional_properties
        return get_brand_template_dataset_response_dataset

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> ChartDataField | ImageDataField | TextDataField:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: ChartDataField | ImageDataField | TextDataField) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
