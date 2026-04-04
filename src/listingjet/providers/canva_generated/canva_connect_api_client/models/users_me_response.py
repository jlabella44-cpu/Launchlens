from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.team_user_summary import TeamUserSummary


T = TypeVar("T", bound="UsersMeResponse")


@_attrs_define
class UsersMeResponse:
    """
    Attributes:
        team_user (TeamUserSummary): Metadata for the user, consisting of the User ID and Team ID.
    """

    team_user: TeamUserSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        team_user = self.team_user.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "team_user": team_user,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.team_user_summary import TeamUserSummary

        d = dict(src_dict)
        team_user = TeamUserSummary.from_dict(d.pop("team_user"))

        users_me_response = cls(
            team_user=team_user,
        )

        users_me_response.additional_properties = d
        return users_me_response

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
