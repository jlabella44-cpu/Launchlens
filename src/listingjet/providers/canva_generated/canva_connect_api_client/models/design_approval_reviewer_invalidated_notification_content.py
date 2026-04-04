from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.design_approval_reviewer_invalidated_notification_content_type import (
    DesignApprovalReviewerInvalidatedNotificationContentType,
)

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary
    from ..models.team_user_summary import TeamUserSummary


T = TypeVar("T", bound="DesignApprovalReviewerInvalidatedNotificationContent")


@_attrs_define
class DesignApprovalReviewerInvalidatedNotificationContent:
    """The notification content for when a reviewer in a design is invalidated.

    Attributes:
        type_ (DesignApprovalReviewerInvalidatedNotificationContentType):  Example:
            design_approval_reviewer_invalidated.
        receiving_team_user (TeamUserSummary): Metadata for the user, consisting of the User ID and Team ID.
        design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
    """

    type_: DesignApprovalReviewerInvalidatedNotificationContentType
    receiving_team_user: TeamUserSummary
    design: DesignSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        receiving_team_user = self.receiving_team_user.to_dict()

        design = self.design.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "receiving_team_user": receiving_team_user,
                "design": design,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary
        from ..models.team_user_summary import TeamUserSummary

        d = dict(src_dict)
        type_ = DesignApprovalReviewerInvalidatedNotificationContentType(d.pop("type"))

        receiving_team_user = TeamUserSummary.from_dict(d.pop("receiving_team_user"))

        design = DesignSummary.from_dict(d.pop("design"))

        design_approval_reviewer_invalidated_notification_content = cls(
            type_=type_,
            receiving_team_user=receiving_team_user,
            design=design,
        )

        design_approval_reviewer_invalidated_notification_content.additional_properties = d
        return design_approval_reviewer_invalidated_notification_content

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
