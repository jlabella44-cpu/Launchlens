from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Team")


@_attrs_define
class Team:
    """Metadata for the Canva Team, consisting of the Team ID,
    display name, and whether it's an external Canva Team.

        Attributes:
            id (str): The ID of the Canva Team. Example: Oi2RJILTrKk0KRhRUZozX.
            display_name (str): The name of the Canva Team as shown in the Canva UI. Example: Acme Corporation.
            external (bool): Is the user making the API call (the authenticated user) from the Canva Team shown?

                - When `true`, the user isn't in the Canva Team shown.
                - When `false`, the user is in the Canva Team shown.
    """

    id: str
    display_name: str
    external: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        display_name = self.display_name

        external = self.external

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "display_name": display_name,
                "external": external,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        display_name = d.pop("display_name")

        external = d.pop("external")

        team = cls(
            id=id,
            display_name=display_name,
            external=external,
        )

        team.additional_properties = d
        return team

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
