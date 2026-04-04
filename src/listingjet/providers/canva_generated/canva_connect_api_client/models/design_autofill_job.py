from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_autofill_status import DesignAutofillStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.autofill_error import AutofillError
    from ..models.create_design_autofill_job_result import CreateDesignAutofillJobResult


T = TypeVar("T", bound="DesignAutofillJob")


@_attrs_define
class DesignAutofillJob:
    """Details about the autofill job.

    Attributes:
        id (str): ID of the asynchronous job that is creating the design using the provided data. Example:
            450a76e7-f96f-43ae-9c37-0e1ce492ac72.
        status (DesignAutofillStatus): Status of the design autofill job. Example: success.
        result (CreateDesignAutofillJobResult | Unset): Design has been created and saved to user's root folder.
        error (AutofillError | Unset): If the autofill job fails, this object provides details about the error.
    """

    id: str
    status: DesignAutofillStatus
    result: CreateDesignAutofillJobResult | Unset = UNSET
    error: AutofillError | Unset = UNSET
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
        from ..models.autofill_error import AutofillError
        from ..models.create_design_autofill_job_result import CreateDesignAutofillJobResult

        d = dict(src_dict)
        id = d.pop("id")

        status = DesignAutofillStatus(d.pop("status"))

        _result = d.pop("result", UNSET)
        result: CreateDesignAutofillJobResult | Unset
        if isinstance(_result, Unset):
            result = UNSET
        else:
            result = CreateDesignAutofillJobResult.from_dict(_result)

        _error = d.pop("error", UNSET)
        error: AutofillError | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = AutofillError.from_dict(_error)

        design_autofill_job = cls(
            id=id,
            status=status,
            result=result,
            error=error,
        )

        design_autofill_job.additional_properties = d
        return design_autofill_job

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
