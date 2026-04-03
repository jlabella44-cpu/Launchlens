from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.asset_upload_job import AssetUploadJob


T = TypeVar("T", bound="GetAssetUploadJobResponse")


@_attrs_define
class GetAssetUploadJobResponse:
    """
    Attributes:
        job (AssetUploadJob): The status of the asset upload job. Example: {'id':
            'e08861ae-3b29-45db-8dc1-1fe0bf7f1cc8', 'status': 'success', 'asset': {'id': 'Msd59349ff', 'type': 'image',
            'name': 'My Awesome Upload', 'tags': ['image', 'holiday', 'best day ever'], 'owner': {'user_id':
            'oU123456AbCdE', 'team_id': 'oB123456AbCdE'}, 'created_at': 1377396000, 'updated_at': 1692928800, 'thumbnail':
            {'width': 595, 'height': 335, 'url': 'https://document-
            export.canva.com/Vczz9/zF9vzVtdADc/2/thumbnail/0001.png?<query-string>'}}}.
    """

    job: AssetUploadJob
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        job = self.job.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "job": job,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.asset_upload_job import AssetUploadJob

        d = dict(src_dict)
        job = AssetUploadJob.from_dict(d.pop("job"))

        get_asset_upload_job_response = cls(
            job=job,
        )

        get_asset_upload_job_response.additional_properties = d
        return get_asset_upload_job_response

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
