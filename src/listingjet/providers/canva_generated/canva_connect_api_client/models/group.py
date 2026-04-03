from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Group")


@_attrs_define
class Group:
    """Metadata for the Canva Group, consisting of the Group ID,
    display name, and whether it's an external Canva Group.

        Attributes:
            id (str): The ID of the group with permissions to access the design. Example: dl9n9SoWoExMsw6Ri1iTg.
            external (bool): Is the user making the API call (the authenticated user) and the Canva Group
                from different Canva Teams?

                - When `true`, the user and the group aren't in the same Canva Team.
                - When `false`, the user and the group are in the same Canva Team.
            display_name (str | Unset): The display name of the group. Example: Sales team.
    """

    id: str
    external: bool
    display_name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        external = self.external

        display_name = self.display_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "external": external,
            }
        )
        if display_name is not UNSET:
            field_dict["display_name"] = display_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        external = d.pop("external")

        display_name = d.pop("display_name", UNSET)

        group = cls(
            id=id,
            external=external,
            display_name=display_name,
        )

        group.additional_properties = d
        return group

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
