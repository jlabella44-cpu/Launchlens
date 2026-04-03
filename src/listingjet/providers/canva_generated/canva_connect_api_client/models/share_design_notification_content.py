from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.share_design_notification_content_type import ShareDesignNotificationContentType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_summary import DesignSummary
    from ..models.share_action import ShareAction
    from ..models.team_user import TeamUser
    from ..models.user import User


T = TypeVar("T", bound="ShareDesignNotificationContent")


@_attrs_define
class ShareDesignNotificationContent:
    """The notification content for when someone shares a design.

    Attributes:
        type_ (ShareDesignNotificationContentType):  Example: share_design.
        triggering_user (User): Metadata for the user, consisting of the User ID and display name.
        receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
        share_url (str): A URL that the user who receives the notification can use to access the shared design. Example:
            https://www.canva.com/api/action?token=zWiz3GqRaWVkolwSgfBa9sKbsKgfHAoxv_mjs-mlX2M.
        share (ShareAction | Unset): Metadata about the share event.
    """

    type_: ShareDesignNotificationContentType
    triggering_user: User
    receiving_team_user: TeamUser
    design: DesignSummary
    share_url: str
    share: ShareAction | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        design = self.design.to_dict()

        share_url = self.share_url

        share: dict[str, Any] | Unset = UNSET
        if not isinstance(self.share, Unset):
            share = self.share.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_team_user": receiving_team_user,
                "design": design,
                "share_url": share_url,
            }
        )
        if share is not UNSET:
            field_dict["share"] = share

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_summary import DesignSummary
        from ..models.share_action import ShareAction
        from ..models.team_user import TeamUser
        from ..models.user import User

        d = dict(src_dict)
        type_ = ShareDesignNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        design = DesignSummary.from_dict(d.pop("design"))

        share_url = d.pop("share_url")

        _share = d.pop("share", UNSET)
        share: ShareAction | Unset
        if isinstance(_share, Unset):
            share = UNSET
        else:
            share = ShareAction.from_dict(_share)

        share_design_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            design=design,
            share_url=share_url,
            share=share,
        )

        share_design_notification_content.additional_properties = d
        return share_design_notification_content

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
