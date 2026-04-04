from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="TeamUserSummary")


@_attrs_define
class TeamUserSummary:
    """Metadata for the user, consisting of the User ID and Team ID.

    Attributes:
        user_id (str): The ID of the user. Example: auDAbliZ2rQNNOsUl5OLu.
        team_id (str): The ID of the user's Canva Team. Example: Oi2RJILTrKk0KRhRUZozX.
    """

    user_id: str
    team_id: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        user_id = self.user_id

        team_id = self.team_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "user_id": user_id,
                "team_id": team_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        user_id = d.pop("user_id")

        team_id = d.pop("team_id")

        team_user_summary = cls(
            user_id=user_id,
            team_id=team_id,
        )

        team_user_summary.additional_properties = d
        return team_user_summary

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
