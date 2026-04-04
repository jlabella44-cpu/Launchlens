from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.asset_type import AssetType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.thumbnail import Thumbnail


T = TypeVar("T", bound="AssetSummary")


@_attrs_define
class AssetSummary:
    """An object representing an asset with associated metadata.

    Attributes:
        type_ (AssetType): Type of an asset. Example: image.
        id (str): The ID of the asset. Example: Msd59349ff.
        name (str): The name of the asset. Example: My Awesome Upload.
        tags (list[str]): The user-facing tags attached to the asset.
            Users can add these tags to their uploaded assets, and they can search their uploaded
            assets in the Canva UI by searching for these tags. For information on how users use
            tags, see the
            [Canva Help Center page on asset tags](https://www.canva.com/help/add-edit-tags/). Example: ['image', 'holiday',
            'best day ever'].
        created_at (int): When the asset was added to Canva, as a Unix timestamp (in seconds since the Unix
            Epoch). Example: 1377396000.
        updated_at (int): When the asset was last updated in Canva, as a Unix timestamp (in seconds since the
            Unix Epoch). Example: 1692928800.
        thumbnail (Thumbnail | Unset): A thumbnail image representing the object.
    """

    type_: AssetType
    id: str
    name: str
    tags: list[str]
    created_at: int
    updated_at: int
    thumbnail: Thumbnail | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = self.id

        name = self.name

        tags = self.tags

        created_at = self.created_at

        updated_at = self.updated_at

        thumbnail: dict[str, Any] | Unset = UNSET
        if not isinstance(self.thumbnail, Unset):
            thumbnail = self.thumbnail.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "id": id,
                "name": name,
                "tags": tags,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if thumbnail is not UNSET:
            field_dict["thumbnail"] = thumbnail

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.thumbnail import Thumbnail

        d = dict(src_dict)
        type_ = AssetType(d.pop("type"))

        id = d.pop("id")

        name = d.pop("name")

        tags = cast(list[str], d.pop("tags"))

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        _thumbnail = d.pop("thumbnail", UNSET)
        thumbnail: Thumbnail | Unset
        if isinstance(_thumbnail, Unset):
            thumbnail = UNSET
        else:
            thumbnail = Thumbnail.from_dict(_thumbnail)

        asset_summary = cls(
            type_=type_,
            id=id,
            name=name,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at,
            thumbnail=thumbnail,
        )

        asset_summary.additional_properties = d
        return asset_summary

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
