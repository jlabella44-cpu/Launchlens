from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_brand_template_dataset_response_dataset import GetBrandTemplateDatasetResponseDataset


T = TypeVar("T", bound="GetBrandTemplateDatasetResponse")


@_attrs_define
class GetBrandTemplateDatasetResponse:
    """Successful response from a `getBrandTemplateDataset` request.

    Attributes:
        dataset (GetBrandTemplateDatasetResponseDataset | Unset): The dataset definition for the brand template. The
            dataset definition contains the data inputs available for use with the
            [Create design autofill job API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-
            autofill-job/). Example: {'cute_pet_image_of_the_day': {'type': 'image'}, 'cute_pet_witty_pet_says': {'type':
            'text'}, 'cute_pet_sales_chart': {'type': 'chart'}}.
    """

    dataset: GetBrandTemplateDatasetResponseDataset | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        dataset: dict[str, Any] | Unset = UNSET
        if not isinstance(self.dataset, Unset):
            dataset = self.dataset.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if dataset is not UNSET:
            field_dict["dataset"] = dataset

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_brand_template_dataset_response_dataset import GetBrandTemplateDatasetResponseDataset

        d = dict(src_dict)
        _dataset = d.pop("dataset", UNSET)
        dataset: GetBrandTemplateDatasetResponseDataset | Unset
        if isinstance(_dataset, Unset):
            dataset = UNSET
        else:
            dataset = GetBrandTemplateDatasetResponseDataset.from_dict(_dataset)

        get_brand_template_dataset_response = cls(
            dataset=dataset,
        )

        get_brand_template_dataset_response.additional_properties = d
        return get_brand_template_dataset_response

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
