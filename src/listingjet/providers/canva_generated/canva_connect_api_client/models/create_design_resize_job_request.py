from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.custom_design_type_input import CustomDesignTypeInput
    from ..models.preset_design_type_input import PresetDesignTypeInput


T = TypeVar("T", bound="CreateDesignResizeJobRequest")


@_attrs_define
class CreateDesignResizeJobRequest:
    """Body parameters for starting a resize job for a design.
    It must include a design ID, and one of the supported design type.

        Attributes:
            design_id (str): The design ID.
            design_type (CustomDesignTypeInput | PresetDesignTypeInput): The desired design type.
    """

    design_id: str
    design_type: CustomDesignTypeInput | PresetDesignTypeInput
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.preset_design_type_input import PresetDesignTypeInput

        design_id = self.design_id

        design_type: dict[str, Any]
        if isinstance(self.design_type, PresetDesignTypeInput):
            design_type = self.design_type.to_dict()
        else:
            design_type = self.design_type.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "design_id": design_id,
                "design_type": design_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.custom_design_type_input import CustomDesignTypeInput
        from ..models.preset_design_type_input import PresetDesignTypeInput

        d = dict(src_dict)
        design_id = d.pop("design_id")

        def _parse_design_type(data: object) -> CustomDesignTypeInput | PresetDesignTypeInput:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_design_type_input_type_0 = PresetDesignTypeInput.from_dict(data)

                return componentsschemas_design_type_input_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_design_type_input_type_1 = CustomDesignTypeInput.from_dict(data)

            return componentsschemas_design_type_input_type_1

        design_type = _parse_design_type(d.pop("design_type"))

        create_design_resize_job_request = cls(
            design_id=design_id,
            design_type=design_type,
        )

        create_design_resize_job_request.additional_properties = d
        return create_design_resize_job_request

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
