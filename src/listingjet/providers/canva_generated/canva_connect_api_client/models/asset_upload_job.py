from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.asset_upload_status import AssetUploadStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.asset import Asset
    from ..models.asset_upload_error import AssetUploadError


T = TypeVar("T", bound="AssetUploadJob")


@_attrs_define
class AssetUploadJob:
    """The status of the asset upload job.

    Example:
        {'id': 'e08861ae-3b29-45db-8dc1-1fe0bf7f1cc8', 'status': 'success', 'asset': {'id': 'Msd59349ff', 'type':
            'image', 'name': 'My Awesome Upload', 'tags': ['image', 'holiday', 'best day ever'], 'owner': {'user_id':
            'oU123456AbCdE', 'team_id': 'oB123456AbCdE'}, 'created_at': 1377396000, 'updated_at': 1692928800, 'thumbnail':
            {'width': 595, 'height': 335, 'url': 'https://document-
            export.canva.com/Vczz9/zF9vzVtdADc/2/thumbnail/0001.png?<query-string>'}}}

    Attributes:
        id (str): The ID of the asset upload job. Example: e08861ae-3b29-45db-8dc1-1fe0bf7f1cc8.
        status (AssetUploadStatus): Status of the asset upload job. Example: success.
        error (AssetUploadError | Unset): If the upload fails, this object provides details about the error.
        asset (Asset | Unset): The asset object, which contains metadata about the asset.
    """

    id: str
    status: AssetUploadStatus
    error: AssetUploadError | Unset = UNSET
    asset: Asset | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        status = self.status.value

        error: dict[str, Any] | Unset = UNSET
        if not isinstance(self.error, Unset):
            error = self.error.to_dict()

        asset: dict[str, Any] | Unset = UNSET
        if not isinstance(self.asset, Unset):
            asset = self.asset.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "status": status,
            }
        )
        if error is not UNSET:
            field_dict["error"] = error
        if asset is not UNSET:
            field_dict["asset"] = asset

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.asset import Asset
        from ..models.asset_upload_error import AssetUploadError

        d = dict(src_dict)
        id = d.pop("id")

        status = AssetUploadStatus(d.pop("status"))

        _error = d.pop("error", UNSET)
        error: AssetUploadError | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = AssetUploadError.from_dict(_error)

        _asset = d.pop("asset", UNSET)
        asset: Asset | Unset
        if isinstance(_asset, Unset):
            asset = UNSET
        else:
            asset = Asset.from_dict(_asset)

        asset_upload_job = cls(
            id=id,
            status=status,
            error=error,
            asset=asset,
        )

        asset_upload_job.additional_properties = d
        return asset_upload_job

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
