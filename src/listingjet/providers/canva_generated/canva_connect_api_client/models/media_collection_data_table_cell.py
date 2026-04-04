from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.media_collection_data_table_cell_type import MediaCollectionDataTableCellType

if TYPE_CHECKING:
    from ..models.data_table_image_upload import DataTableImageUpload
    from ..models.data_table_video_upload import DataTableVideoUpload


T = TypeVar("T", bound="MediaCollectionDataTableCell")


@_attrs_define
class MediaCollectionDataTableCell:
    """Cell containing a media collection.

    Attributes:
        type_ (MediaCollectionDataTableCellType):
        value (list[DataTableImageUpload | DataTableVideoUpload]): Media collection values.

            Provide an empty array for an empty cell.
    """

    type_: MediaCollectionDataTableCellType
    value: list[DataTableImageUpload | DataTableVideoUpload]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.data_table_image_upload import DataTableImageUpload

        type_ = self.type_.value

        value = []
        for value_item_data in self.value:
            value_item: dict[str, Any]
            if isinstance(value_item_data, DataTableImageUpload):
                value_item = value_item_data.to_dict()
            else:
                value_item = value_item_data.to_dict()

            value.append(value_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.data_table_image_upload import DataTableImageUpload
        from ..models.data_table_video_upload import DataTableVideoUpload

        d = dict(src_dict)
        type_ = MediaCollectionDataTableCellType(d.pop("type"))

        value = []
        _value = d.pop("value")
        for value_item_data in _value:

            def _parse_value_item(data: object) -> DataTableImageUpload | DataTableVideoUpload:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_data_table_media_type_0 = DataTableImageUpload.from_dict(data)

                    return componentsschemas_data_table_media_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_data_table_media_type_1 = DataTableVideoUpload.from_dict(data)

                return componentsschemas_data_table_media_type_1

            value_item = _parse_value_item(value_item_data)

            value.append(value_item)

        media_collection_data_table_cell = cls(
            type_=type_,
            value=value,
        )

        media_collection_data_table_cell.additional_properties = d
        return media_collection_data_table_cell

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
