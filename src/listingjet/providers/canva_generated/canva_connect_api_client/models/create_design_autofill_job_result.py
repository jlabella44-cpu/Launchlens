from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.create_design_autofill_job_result_type import CreateDesignAutofillJobResultType

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary


T = TypeVar("T", bound="CreateDesignAutofillJobResult")


@_attrs_define
class CreateDesignAutofillJobResult:
    """Design has been created and saved to user's root folder.

    Attributes:
        type_ (CreateDesignAutofillJobResultType):
        design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
    """

    type_: CreateDesignAutofillJobResultType
    design: DesignSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        design = self.design.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "design": design,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary

        d = dict(src_dict)
        type_ = CreateDesignAutofillJobResultType(d.pop("type"))

        design = DesignSummary.from_dict(d.pop("design"))

        create_design_autofill_job_result = cls(
            type_=type_,
            design=design,
        )

        create_design_autofill_job_result.additional_properties = d
        return create_design_autofill_job_result

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
