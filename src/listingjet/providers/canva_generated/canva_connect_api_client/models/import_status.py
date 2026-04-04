from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.import_status_state import ImportStatusState
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.import_error import ImportError_


T = TypeVar("T", bound="ImportStatus")


@_attrs_define
class ImportStatus:
    """The import status of the asset.

    Attributes:
        state (ImportStatusState): State of the import job for an uploaded asset. Example: success.
        error (ImportError_ | Unset): If the import fails, this object provides details about the error.
    """

    state: ImportStatusState
    error: ImportError_ | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        state = self.state.value

        error: dict[str, Any] | Unset = UNSET
        if not isinstance(self.error, Unset):
            error = self.error.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "state": state,
            }
        )
        if error is not UNSET:
            field_dict["error"] = error

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.import_error import ImportError_

        d = dict(src_dict)
        state = ImportStatusState(d.pop("state"))

        _error = d.pop("error", UNSET)
        error: ImportError_ | Unset
        if isinstance(_error, Unset):
            error = UNSET
        else:
            error = ImportError_.from_dict(_error)

        import_status = cls(
            state=state,
            error=error,
        )

        import_status.additional_properties = d
        return import_status

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
