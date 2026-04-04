from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_approval_requested_notification_content_type import DesignApprovalRequestedNotificationContentType

if TYPE_CHECKING:
    from ..models.approval_request_action import ApprovalRequestAction
    from ..models.design_summary import DesignSummary
    from ..models.group import Group
    from ..models.team_user import TeamUser
    from ..models.user import User


T = TypeVar("T", bound="DesignApprovalRequestedNotificationContent")


@_attrs_define
class DesignApprovalRequestedNotificationContent:
    """The notification content for when someone requests a user to
    [approve a design](https://www.canva.com/help/get-approval/).

        Attributes:
            type_ (DesignApprovalRequestedNotificationContentType):  Example: design_approval_requested.
            triggering_user (User): Metadata for the user, consisting of the User ID and display name.
            initial_requesting_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
            receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
            requested_groups (list[Group]):
            design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
            approve_url (str): A URL, which is scoped only to the user requested to review the design, that links to
                the design with the approval UI opened. Example:
                https://canva.com/api/action?token=HZb0lLHaEhNkT1qQrAwoe0-8SqyXUgJ4vnHGvN2rLZ0.
            approval_request (ApprovalRequestAction): Metadata about the design approval request.
    """

    type_: DesignApprovalRequestedNotificationContentType
    triggering_user: User
    initial_requesting_user: TeamUser
    receiving_team_user: TeamUser
    requested_groups: list[Group]
    design: DesignSummary
    approve_url: str
    approval_request: ApprovalRequestAction
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        initial_requesting_user = self.initial_requesting_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        requested_groups = []
        for requested_groups_item_data in self.requested_groups:
            requested_groups_item = requested_groups_item_data.to_dict()
            requested_groups.append(requested_groups_item)

        design = self.design.to_dict()

        approve_url = self.approve_url

        approval_request = self.approval_request.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "initial_requesting_user": initial_requesting_user,
                "receiving_team_user": receiving_team_user,
                "requested_groups": requested_groups,
                "design": design,
                "approve_url": approve_url,
                "approval_request": approval_request,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.approval_request_action import ApprovalRequestAction
        from ..models.design_summary import DesignSummary
        from ..models.group import Group
        from ..models.team_user import TeamUser
        from ..models.user import User

        d = dict(src_dict)
        type_ = DesignApprovalRequestedNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        initial_requesting_user = TeamUser.from_dict(d.pop("initial_requesting_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        requested_groups = []
        _requested_groups = d.pop("requested_groups")
        for requested_groups_item_data in _requested_groups:
            requested_groups_item = Group.from_dict(requested_groups_item_data)

            requested_groups.append(requested_groups_item)

        design = DesignSummary.from_dict(d.pop("design"))

        approve_url = d.pop("approve_url")

        approval_request = ApprovalRequestAction.from_dict(d.pop("approval_request"))

        design_approval_requested_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            initial_requesting_user=initial_requesting_user,
            receiving_team_user=receiving_team_user,
            requested_groups=requested_groups,
            design=design,
            approve_url=approve_url,
            approval_request=approval_request,
        )

        design_approval_requested_notification_content.additional_properties = d
        return design_approval_requested_notification_content

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
