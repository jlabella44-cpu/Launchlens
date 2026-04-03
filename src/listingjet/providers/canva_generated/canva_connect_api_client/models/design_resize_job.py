from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_resize_status import DesignResizeStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_resize_error import DesignResizeError
    from ..models.design_resize_job_result import DesignResizeJobResult


T = TypeVar("T", bound="DesignResizeJob")


@_attrs_define
class DesignResizeJob:
    """Details about the design resize job.

    Attributes:
        id (str): The design resize job ID. Example: bbd8dfcd-ead1-4871-81d5-962bfec82274.
        status (DesignResizeStatus): Status of the design resize job. Example: success.
        result (DesignResizeJobResult | Unset): Design has been created and saved to user's root
            ([projects](https://www.canva.com/help/find-designs-and-folders/)) folder.
        error (DesignResizeError | Unset): If the design resize job fails, this object provides details about the error.
    """

    id: str
    status: DesignResizeStatus
    result: DesignResizeJobResult | Unset = UNSET
    error: DesignResizeError | Unset = UNSET
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
        from ..models.design_resize_error import DesignResizeError
        from ..models.design_resize_job_result import DesignResizeJobResult

        d = dict(src_dict)
        id = d.pop("id")

        status = DesignResizeStatus(d.pop("status"))

        _result = d.pop("result", UNSET)
        result: DesignResizeJobResult | Unset
        if isinstance(_result, Unset):
            result = UNSET
        else:
            result = DesignResizeJobResult.from_dict(_result)

        _error = d.pop("error", UNSET)
        error: DesignResizeError | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = DesignResizeError.from_dict(_error)

        design_resize_job = cls(
            id=id,
            status=status,
            result=result,
            error=error,
        )

        design_resize_job.additional_properties = d
        return design_resize_job

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
