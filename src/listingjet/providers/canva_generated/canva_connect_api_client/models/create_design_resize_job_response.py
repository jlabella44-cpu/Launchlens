from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.design_resize_job import DesignResizeJob


T = TypeVar("T", bound="CreateDesignResizeJobResponse")


@_attrs_define
class CreateDesignResizeJobResponse:
    """
    Attributes:
        job (DesignResizeJob): Details about the design resize job.
    """

    job: DesignResizeJob
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
        from ..models.design_resize_job import DesignResizeJob

        d = dict(src_dict)
        job = DesignResizeJob.from_dict(d.pop("job"))

        create_design_resize_job_response = cls(
            job=job,
        )

        create_design_resize_job_response.additional_properties = d
        return create_design_resize_job_response

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
