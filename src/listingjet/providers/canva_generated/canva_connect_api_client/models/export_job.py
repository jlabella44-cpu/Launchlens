from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_export_status import DesignExportStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.export_error import ExportError


T = TypeVar("T", bound="ExportJob")


@_attrs_define
class ExportJob:
    """The status of the export job.

    Attributes:
        id (str): The export job ID. Example: e08861ae-3b29-45db-8dc1-1fe0bf7f1cc8.
        status (DesignExportStatus): The export status of the job. A newly created job will be `in_progress` and will
            eventually
            become `success` or `failed`.
        urls (list[str] | Unset): Download URL(s) for the completed export job. These URLs expire after 24 hours.

            Depending on the design type and export format, there is a download URL for each page in the design. The list is
            sorted by page order. Example: ['https://export-download.canva-dev.com/...'].
        error (ExportError | Unset): If the export fails, this object provides details about the error.
    """

    id: str
    status: DesignExportStatus
    urls: list[str] | Unset = UNSET
    error: ExportError | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        status = self.status.value

        urls: list[str] | Unset = UNSET
        if not isinstance(self.urls, Unset):
            urls = self.urls

        error: dict[str, Any] | Unset = UNSET
        if not isinstance(self.error, Unset):
            error = self.error.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "status": status,
            }
        )
        if urls is not UNSET:
            field_dict["urls"] = urls
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.export_error import ExportError

        d = dict(src_dict)
        id = d.pop("id")

        status = DesignExportStatus(d.pop("status"))

        urls = cast(list[str], d.pop("urls", UNSET))

        _error = d.pop("error", UNSET)
        error: ExportError | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = ExportError.from_dict(_error)

        export_job = cls(
            id=id,
            status=status,
            urls=urls,
            error=error,
        )

        export_job.additional_properties = d
        return export_job

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
