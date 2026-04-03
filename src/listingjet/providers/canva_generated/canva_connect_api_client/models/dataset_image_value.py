from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.dataset_image_value_type import DatasetImageValueType

T = TypeVar("T", bound="DatasetImageValue")


@_attrs_define
class DatasetImageValue:
    """If the data field is an image field.

    Attributes:
        type_ (DatasetImageValueType):
        asset_id (str): `asset_id` of the image to insert into the template element. Example: Msd59349ff.
    """

    type_: DatasetImageValueType
    asset_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        asset_id = self.asset_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "asset_id": asset_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = DatasetImageValueType(d.pop("type"))

        asset_id = d.pop("asset_id")

        dataset_image_value = cls(
            type_=type_,
            asset_id=asset_id,
        )

        dataset_image_value.additional_properties = d
        return dataset_image_value

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
