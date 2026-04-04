from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary


T = TypeVar("T", bound="DesignImportJobResult")


@_attrs_define
class DesignImportJobResult:
    """
    Attributes:
        designs (list[DesignSummary]): A list of designs imported from the external file. It usually contains one item.
            Imports with a large number of pages or assets are split into multiple designs.
    """

    designs: list[DesignSummary]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        designs = []
        for designs_item_data in self.designs:
            designs_item = designs_item_data.to_dict()
            designs.append(designs_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "designs": designs,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary

        d = dict(src_dict)
        designs = []
        _designs = d.pop("designs")
        for designs_item_data in _designs:
            designs_item = DesignSummary.from_dict(designs_item_data)

            designs.append(designs_item)

        design_import_job_result = cls(
            designs=designs,
        )

        design_import_job_result.additional_properties = d
        return design_import_job_result

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
