from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_access_requested_notification_content_type import DesignAccessRequestedNotificationContentType

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary
    from ..models.team_user import TeamUser


T = TypeVar("T", bound="DesignAccessRequestedNotificationContent")


@_attrs_define
class DesignAccessRequestedNotificationContent:
    """The notification content for when someone requests access to a design.

    Attributes:
        type_ (DesignAccessRequestedNotificationContentType):  Example: design_access_requested.
        triggering_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
        grant_access_url (str): A URL, which is scoped only to the user that can grant the requested access to the
            design, that approves the requested access. Example:
            https://www.canva.com/api/action?token=OosRN8M_eO2-QbLpUmP5JCwTMSXWfadtQYWuj9WKzoE.
    """

    type_: DesignAccessRequestedNotificationContentType
    triggering_user: TeamUser
    receiving_team_user: TeamUser
    design: DesignSummary
    grant_access_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        design = self.design.to_dict()

        grant_access_url = self.grant_access_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_team_user": receiving_team_user,
                "design": design,
                "grant_access_url": grant_access_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary
        from ..models.team_user import TeamUser

        d = dict(src_dict)
        type_ = DesignAccessRequestedNotificationContentType(d.pop("type"))

        triggering_user = TeamUser.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        design = DesignSummary.from_dict(d.pop("design"))

        grant_access_url = d.pop("grant_access_url")

        design_access_requested_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            design=design,
            grant_access_url=grant_access_url,
        )

        design_access_requested_notification_content.additional_properties = d
        return design_access_requested_notification_content

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
