from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TeamUser")


@_attrs_define
class TeamUser:
    """Metadata for the user, consisting of the User ID, Team ID, and display name.

    Attributes:
        user_id (str | Unset): The ID of the user. Example: auDAbliZ2rQNNOsUl5OLu.
        team_id (str | Unset): The ID of the user's Canva Team. Example: Oi2RJILTrKk0KRhRUZozX.
        display_name (str | Unset): The name of the user as shown in the Canva UI. Example: Jane Doe.
    """

    user_id: str | Unset = UNSET
    team_id: str | Unset = UNSET
    display_name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        user_id = self.user_id

        team_id = self.team_id

        display_name = self.display_name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if user_id is not UNSET:
            field_dict["user_id"] = user_id
        if team_id is not UNSET:
            field_dict["team_id"] = team_id
        if display_name is not UNSET:
            field_dict["display_name"] = display_name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        user_id = d.pop("user_id", UNSET)

        team_id = d.pop("team_id", UNSET)

        display_name = d.pop("display_name", UNSET)

        team_user = cls(
            user_id=user_id,
            team_id=team_id,
            display_name=display_name,
        )

        team_user.additional_properties = d
        return team_user

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
