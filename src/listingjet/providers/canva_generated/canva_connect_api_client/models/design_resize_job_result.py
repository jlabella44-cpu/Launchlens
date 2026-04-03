from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary
    from ..models.trial_information import TrialInformation


T = TypeVar("T", bound="DesignResizeJobResult")


@_attrs_define
class DesignResizeJobResult:
    """Design has been created and saved to user's root
    ([projects](https://www.canva.com/help/find-designs-and-folders/)) folder.

        Attributes:
            design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
            trial_information (TrialInformation | Unset): WARNING: Trials and trial information are a [preview
                feature](https://www.canva.dev/docs/connect/#preview-apis).
                There might be unannounced breaking changes to this feature which won't produce a new API version.
    """

    design: DesignSummary
    trial_information: TrialInformation | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        design = self.design.to_dict()

        trial_information: dict[str, Any] | Unset = UNSET
        if not isinstance(self.trial_information, Unset):
            trial_information = self.trial_information.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "design": design,
            }
        )
        if trial_information is not UNSET:
            field_dict["trial_information"] = trial_information

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary
        from ..models.trial_information import TrialInformation

        d = dict(src_dict)
        design = DesignSummary.from_dict(d.pop("design"))

        _trial_information = d.pop("trial_information", UNSET)
        trial_information: TrialInformation | Unset
        if isinstance(_trial_information, Unset):
            trial_information = UNSET
        else:
            trial_information = TrialInformation.from_dict(_trial_information)

        design_resize_job_result = cls(
            design=design,
            trial_information=trial_information,
        )

        design_resize_job_result.additional_properties = d
        return design_resize_job_result

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
