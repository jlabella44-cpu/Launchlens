from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.export_error_code import ExportErrorCode

T = TypeVar("T", bound="ExportError")


@_attrs_define
class ExportError:
    """If the export fails, this object provides details about the error.

    Attributes:
        code (ExportErrorCode): If the export failed, this specifies the reason why it failed.

            - `license_required`: The design contains [premium elements](https://www.canva.com/help/premium-elements/) that
            haven't been purchased. You can either buy the elements or upgrade to a Canva plan (such as Canva Pro) that has
            premium features, then try again. Alternatively, you can set `export_quality` to `regular` to export your
            document in regular quality.
            - `approval_required`: The design requires [reviewer approval](https://www.canva.com/en_au/help/design-
            approval/) before it can be exported.
            - `internal_failure`: The service encountered an error when exporting your design.
        message (str): A human-readable description of what went wrong.
    """

    code: ExportErrorCode
    message: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        code = self.code.value

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "code": code,
                "message": message,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        code = ExportErrorCode(d.pop("code"))

        message = d.pop("message")

        export_error = cls(
            code=code,
            message=message,
        )

        export_error.additional_properties = d
        return export_error

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
