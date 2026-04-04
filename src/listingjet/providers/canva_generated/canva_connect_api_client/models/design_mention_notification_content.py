from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_mention_notification_content_type import DesignMentionNotificationContentType

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary
    from ..models.team_user import TeamUser
    from ..models.user import User


T = TypeVar("T", bound="DesignMentionNotificationContent")


@_attrs_define
class DesignMentionNotificationContent:
    """The notification content for when someone mentions a user in a design.

    The link to the design in this notification is valid for 30 days, and can only be opened by
    the recipient of the notification.

        Attributes:
            type_ (DesignMentionNotificationContentType):  Example: design_mention.
            triggering_user (User): Metadata for the user, consisting of the User ID and display name.
            receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
            design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
    """

    type_: DesignMentionNotificationContentType
    triggering_user: User
    receiving_team_user: TeamUser
    design: DesignSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        design = self.design.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_team_user": receiving_team_user,
                "design": design,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary
        from ..models.team_user import TeamUser
        from ..models.user import User

        d = dict(src_dict)
        type_ = DesignMentionNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        design = DesignSummary.from_dict(d.pop("design"))

        design_mention_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            design=design,
        )

        design_mention_notification_content.additional_properties = d
        return design_mention_notification_content

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
