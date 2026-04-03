from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.team_invite_notification_content_type import TeamInviteNotificationContentType

if TYPE_CHECKING:
    from ..models.team import Team
    from ..models.user import User


T = TypeVar("T", bound="TeamInviteNotificationContent")


@_attrs_define
class TeamInviteNotificationContent:
    """The notification content for when someone is invited to a
    [Canva team](https://www.canva.com/help/about-canva-for-teams/).

        Attributes:
            type_ (TeamInviteNotificationContentType):  Example: team_invite.
            triggering_user (User): Metadata for the user, consisting of the User ID and display name.
            receiving_user (User): Metadata for the user, consisting of the User ID and display name.
            inviting_team (Team): Metadata for the Canva Team, consisting of the Team ID,
                display name, and whether it's an external Canva Team.
    """

    type_: TeamInviteNotificationContentType
    triggering_user: User
    receiving_user: User
    inviting_team: Team
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_user = self.receiving_user.to_dict()

        inviting_team = self.inviting_team.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_user": receiving_user,
                "inviting_team": inviting_team,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.team import Team
        from ..models.user import User

        d = dict(src_dict)
        type_ = TeamInviteNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        receiving_user = User.from_dict(d.pop("receiving_user"))

        inviting_team = Team.from_dict(d.pop("inviting_team"))

        team_invite_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_user=receiving_user,
            inviting_team=inviting_team,
        )

        team_invite_notification_content.additional_properties = d
        return team_invite_notification_content

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
