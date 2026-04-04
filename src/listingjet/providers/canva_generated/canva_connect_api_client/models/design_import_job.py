from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_import_status import DesignImportStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_import_error import DesignImportError
    from ..models.design_import_job_result import DesignImportJobResult


T = TypeVar("T", bound="DesignImportJob")


@_attrs_define
class DesignImportJob:
    """The status of the design import job.

    Attributes:
        id (str): The ID of the design import job. Example: e08861ae-3b29-45db-8dc1-1fe0bf7f1cc8.
        status (DesignImportStatus): The status of the design import job. Example: success.
        result (DesignImportJobResult | Unset):
        error (DesignImportError | Unset): If the import job fails, this object provides details about the error.
    """

    id: str
    status: DesignImportStatus
    result: DesignImportJobResult | Unset = UNSET
    error: DesignImportError | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        status = self.status.value

        result: dict[str, Any] | Unset = UNSET
        if not isinstance(self.result, Unset):
            result = self.result.to_dict()

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
        if result is not UNSET:
            field_dict["result"] = result
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_import_error import DesignImportError
        from ..models.design_import_job_result import DesignImportJobResult

        d = dict(src_dict)
        id = d.pop("id")

        status = DesignImportStatus(d.pop("status"))

        _result = d.pop("result", UNSET)
        result: DesignImportJobResult | Unset
        if isinstance(_result, Unset):
            result = UNSET
        else:
            result = DesignImportJobResult.from_dict(_result)

        _error = d.pop("error", UNSET)
        error: DesignImportError | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = DesignImportError.from_dict(_error)

        design_import_job = cls(
            id=id,
            status=status,
            result=result,
            error=error,
        )

        design_import_job.additional_properties = d
        return design_import_job

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
