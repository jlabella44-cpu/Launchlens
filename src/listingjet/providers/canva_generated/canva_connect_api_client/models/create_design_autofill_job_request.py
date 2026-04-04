from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.create_design_autofill_job_request_data import CreateDesignAutofillJobRequestData


T = TypeVar("T", bound="CreateDesignAutofillJobRequest")


@_attrs_define
class CreateDesignAutofillJobRequest:
    """
    Attributes:
        brand_template_id (str): ID of the input brand template. Example: DAFVztcvd9z.
        data (CreateDesignAutofillJobRequestData): Data object containing the data fields and values to autofill.
            Example: {'cute_pet_image_of_the_day': {'type': 'image', 'asset_id': 'Msd59349ff'}, 'cute_pet_witty_pet_says':
            {'type': 'text', 'text': 'It was like this when I got here!'}, 'cute_pet_sales_chart': {'type': 'chart',
            'chart_data': {'column_configs': [{'name': 'Geographic Region', 'type': 'string'}, {'name': 'Sales (millions
            AUD)', 'type': 'number'}, {'name': 'Target (millions AUD)', 'type': 'number'}, {'name': 'Target met?', 'type':
            'boolean'}, {'name': 'Date met', 'type': 'date'}], 'rows': [{'cells': [{'type': 'string', 'value': 'Asia
            Pacific'}, {'type': 'number', 'value': 10.2}, {'type': 'number', 'value': 10}, {'type': 'boolean', 'value':
            True}, {'type': 'date', 'value': 1721944387}]}, {'cells': [{'type': 'string', 'value': 'EMEA'}, {'type':
            'number', 'value': 13.8}, {'type': 'number', 'value': 14}, {'type': 'boolean', 'value': False}, {'type':
            'date'}]}]}}}.
        title (str | Unset): Title to use for the autofilled design.

            If no design title is provided, the autofilled design will have the same title as the brand template.
    """

    brand_template_id: str
    data: CreateDesignAutofillJobRequestData
    title: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        brand_template_id = self.brand_template_id

        data = self.data.to_dict()

        title = self.title

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "brand_template_id": brand_template_id,
                "data": data,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.create_design_autofill_job_request_data import CreateDesignAutofillJobRequestData

        d = dict(src_dict)
        brand_template_id = d.pop("brand_template_id")

        data = CreateDesignAutofillJobRequestData.from_dict(d.pop("data"))

        title = d.pop("title", UNSET)

        create_design_autofill_job_request = cls(
            brand_template_id=brand_template_id,
            data=data,
            title=title,
        )

        create_design_autofill_job_request.additional_properties = d
        return create_design_autofill_job_request

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
