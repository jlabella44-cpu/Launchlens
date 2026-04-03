from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_type_create_design_request_type import DesignTypeCreateDesignRequestType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.custom_design_type_input import CustomDesignTypeInput
    from ..models.preset_design_type_input import PresetDesignTypeInput


T = TypeVar("T", bound="DesignTypeCreateDesignRequest")


@_attrs_define
class DesignTypeCreateDesignRequest:
    """Create a design by specifying the design type and/or an asset.
    At least one of `design_type` or `asset_id` must be defined.

        Attributes:
            type_ (DesignTypeCreateDesignRequestType): For backward compatibility, if `type` isn't specified in the request,
                the request type will be assumed to be `type_and_asset`.
            design_type (CustomDesignTypeInput | PresetDesignTypeInput | Unset): The desired design type.
            asset_id (str | Unset): The ID of an asset to insert into the created design. Currently, this only supports
                image assets. Example: Msd59349ff.
            title (str | Unset): The name of the design. Example: My Holiday Presentation.
    """

    type_: DesignTypeCreateDesignRequestType
    design_type: CustomDesignTypeInput | PresetDesignTypeInput | Unset = UNSET
    asset_id: str | Unset = UNSET
    title: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.preset_design_type_input import PresetDesignTypeInput

        type_ = self.type_.value

        design_type: dict[str, Any] | Unset
        if isinstance(self.design_type, Unset):
            design_type = UNSET
        elif isinstance(self.design_type, PresetDesignTypeInput):
            design_type = self.design_type.to_dict()
        else:
            design_type = self.design_type.to_dict()

        asset_id = self.asset_id

        title = self.title

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if design_type is not UNSET:
            field_dict["design_type"] = design_type
        if asset_id is not UNSET:
            field_dict["asset_id"] = asset_id
        if title is not UNSET:
            field_dict["title"] = title

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.custom_design_type_input import CustomDesignTypeInput
        from ..models.preset_design_type_input import PresetDesignTypeInput

        d = dict(src_dict)
        type_ = DesignTypeCreateDesignRequestType(d.pop("type"))

        def _parse_design_type(data: object) -> CustomDesignTypeInput | PresetDesignTypeInput | Unset:
            if isinstance(data, Unset):
                return data
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

        design_type = _parse_design_type(d.pop("design_type", UNSET))

        asset_id = d.pop("asset_id", UNSET)

        title = d.pop("title", UNSET)

        design_type_create_design_request = cls(
            type_=type_,
            design_type=design_type,
            asset_id=asset_id,
            title=title,
        )

        design_type_create_design_request.additional_properties = d
        return design_type_create_design_request

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
