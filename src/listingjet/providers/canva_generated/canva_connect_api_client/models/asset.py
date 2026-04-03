from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.asset_type import AssetType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.image_metadata import ImageMetadata
    from ..models.import_status import ImportStatus
    from ..models.team_user_summary import TeamUserSummary
    from ..models.thumbnail import Thumbnail
    from ..models.video_metadata import VideoMetadata


T = TypeVar("T", bound="Asset")


@_attrs_define
class Asset:
    """The asset object, which contains metadata about the asset.

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
        owner (TeamUserSummary): Metadata for the user, consisting of the User ID and Team ID.
        import_status (ImportStatus | Unset): The import status of the asset.
        thumbnail (Thumbnail | Unset): A thumbnail image representing the object.
        metadata (ImageMetadata | Unset | VideoMetadata): Type-specific metadata for the asset.
    """

    type_: AssetType
    id: str
    name: str
    tags: list[str]
    created_at: int
    updated_at: int
    owner: TeamUserSummary
    import_status: ImportStatus | Unset = UNSET
    thumbnail: Thumbnail | Unset = UNSET
    metadata: ImageMetadata | Unset | VideoMetadata = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.image_metadata import ImageMetadata

        type_ = self.type_.value

        id = self.id

        name = self.name

        tags = self.tags

        created_at = self.created_at

        updated_at = self.updated_at

        owner = self.owner.to_dict()

        import_status: dict[str, Any] | Unset = UNSET
        if not isinstance(self.import_status, Unset):
            import_status = self.import_status.to_dict()

        thumbnail: dict[str, Any] | Unset = UNSET
        if not isinstance(self.thumbnail, Unset):
            thumbnail = self.thumbnail.to_dict()

        metadata: dict[str, Any] | Unset
        if isinstance(self.metadata, Unset):
            metadata = UNSET
        elif isinstance(self.metadata, ImageMetadata):
            metadata = self.metadata.to_dict()
        else:
            metadata = self.metadata.to_dict()

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
                "owner": owner,
            }
        )
        if import_status is not UNSET:
            field_dict["import_status"] = import_status
        if thumbnail is not UNSET:
            field_dict["thumbnail"] = thumbnail
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.image_metadata import ImageMetadata
        from ..models.import_status import ImportStatus
        from ..models.team_user_summary import TeamUserSummary
        from ..models.thumbnail import Thumbnail
        from ..models.video_metadata import VideoMetadata

        d = dict(src_dict)
        type_ = AssetType(d.pop("type"))

        id = d.pop("id")

        name = d.pop("name")

        tags = cast(list[str], d.pop("tags"))

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        owner = TeamUserSummary.from_dict(d.pop("owner"))

        _import_status = d.pop("import_status", UNSET)
        import_status: ImportStatus | Unset
        if isinstance(_import_status, Unset):
            import_status = UNSET
        else:
            import_status = ImportStatus.from_dict(_import_status)

        _thumbnail = d.pop("thumbnail", UNSET)
        thumbnail: Thumbnail | Unset
        if isinstance(_thumbnail, Unset):
            thumbnail = UNSET
        else:
            thumbnail = Thumbnail.from_dict(_thumbnail)

        def _parse_metadata(data: object) -> ImageMetadata | Unset | VideoMetadata:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_asset_metadata_type_0 = ImageMetadata.from_dict(data)

                return componentsschemas_asset_metadata_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_asset_metadata_type_1 = VideoMetadata.from_dict(data)

            return componentsschemas_asset_metadata_type_1

        metadata = _parse_metadata(d.pop("metadata", UNSET))

        asset = cls(
            type_=type_,
            id=id,
            name=name,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at,
            owner=owner,
            import_status=import_status,
            thumbnail=thumbnail,
            metadata=metadata,
        )

        asset.additional_properties = d
        return asset

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
