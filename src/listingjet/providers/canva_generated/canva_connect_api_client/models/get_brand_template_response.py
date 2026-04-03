from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.brand_template import BrandTemplate


T = TypeVar("T", bound="GetBrandTemplateResponse")


@_attrs_define
class GetBrandTemplateResponse:
    """Successful response from a `getBrandTemplate` request.

    Attributes:
        brand_template (BrandTemplate): An object representing a brand template with associated metadata.
    """

    brand_template: BrandTemplate
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        brand_template = self.brand_template.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "brand_template": brand_template,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.brand_template import BrandTemplate

        d = dict(src_dict)
        brand_template = BrandTemplate.from_dict(d.pop("brand_template"))

        get_brand_template_response = cls(
            brand_template=brand_template,
        )

        get_brand_template_response.additional_properties = d
        return get_brand_template_response

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
