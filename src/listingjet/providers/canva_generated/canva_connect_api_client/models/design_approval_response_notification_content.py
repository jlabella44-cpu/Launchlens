from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_approval_response_notification_content_type import DesignApprovalResponseNotificationContentType

if TYPE_CHECKING:
    from ..models.approval_response_action import ApprovalResponseAction
    from ..models.design_summary import DesignSummary
    from ..models.group import Group
    from ..models.team_user import TeamUser
    from ..models.user import User


T = TypeVar("T", bound="DesignApprovalResponseNotificationContent")


@_attrs_define
class DesignApprovalResponseNotificationContent:
    """The notification content for when someone approves a design or gives feedback.

    Attributes:
        type_ (DesignApprovalResponseNotificationContentType):  Example: design_approval_response.
        triggering_user (User): Metadata for the user, consisting of the User ID and display name.
        receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        initial_requesting_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        responding_groups (list[Group]):
        design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
        approval_response (ApprovalResponseAction): Metadata about the design approval response.
    """

    type_: DesignApprovalResponseNotificationContentType
    triggering_user: User
    receiving_team_user: TeamUser
    initial_requesting_user: TeamUser
    responding_groups: list[Group]
    design: DesignSummary
    approval_response: ApprovalResponseAction
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        initial_requesting_user = self.initial_requesting_user.to_dict()

        responding_groups = []
        for responding_groups_item_data in self.responding_groups:
            responding_groups_item = responding_groups_item_data.to_dict()
            responding_groups.append(responding_groups_item)

        design = self.design.to_dict()

        approval_response = self.approval_response.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_team_user": receiving_team_user,
                "initial_requesting_user": initial_requesting_user,
                "responding_groups": responding_groups,
                "design": design,
                "approval_response": approval_response,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.approval_response_action import ApprovalResponseAction
        from ..models.design_summary import DesignSummary
        from ..models.group import Group
        from ..models.team_user import TeamUser
        from ..models.user import User

        d = dict(src_dict)
        type_ = DesignApprovalResponseNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        initial_requesting_user = TeamUser.from_dict(d.pop("initial_requesting_user"))

        responding_groups = []
        _responding_groups = d.pop("responding_groups")
        for responding_groups_item_data in _responding_groups:
            responding_groups_item = Group.from_dict(responding_groups_item_data)

            responding_groups.append(responding_groups_item)

        design = DesignSummary.from_dict(d.pop("design"))

        approval_response = ApprovalResponseAction.from_dict(d.pop("approval_response"))

        design_approval_response_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            initial_requesting_user=initial_requesting_user,
            responding_groups=responding_groups,
            design=design,
            approval_response=approval_response,
        )

        design_approval_response_notification_content.additional_properties = d
        return design_approval_response_notification_content

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
