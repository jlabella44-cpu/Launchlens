from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.folder_access_requested_notification_content_type import FolderAccessRequestedNotificationContentType

if TYPE_CHECKING:
    from ..models.folder_summary import FolderSummary
    from ..models.team_user import TeamUser


T = TypeVar("T", bound="FolderAccessRequestedNotificationContent")


@_attrs_define
class FolderAccessRequestedNotificationContent:
    """The notification content for when someone requests access to a folder.

    Attributes:
        type_ (FolderAccessRequestedNotificationContentType):  Example: folder_access_requested.
        triggering_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        folder (FolderSummary): This object contains some folder metadata. You can retrieve additional metadata
            using the folder ID and the `/v1/folders/{folderId}` endpoint.
    """

    type_: FolderAccessRequestedNotificationContentType
    triggering_user: TeamUser
    receiving_team_user: TeamUser
    folder: FolderSummary
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        folder = self.folder.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_team_user": receiving_team_user,
                "folder": folder,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.folder_summary import FolderSummary
        from ..models.team_user import TeamUser

        d = dict(src_dict)
        type_ = FolderAccessRequestedNotificationContentType(d.pop("type"))

        triggering_user = TeamUser.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        folder = FolderSummary.from_dict(d.pop("folder"))

        folder_access_requested_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            folder=folder,
        )

        folder_access_requested_notification_content.additional_properties = d
        return folder_access_requested_notification_content

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
