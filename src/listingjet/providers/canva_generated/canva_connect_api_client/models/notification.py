from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.comment_notification_content import CommentNotificationContent
    from ..models.design_access_requested_notification_content import DesignAccessRequestedNotificationContent
    from ..models.design_approval_requested_notification_content import DesignApprovalRequestedNotificationContent
    from ..models.design_approval_response_notification_content import DesignApprovalResponseNotificationContent
    from ..models.design_approval_reviewer_invalidated_notification_content import (
        DesignApprovalReviewerInvalidatedNotificationContent,
    )
    from ..models.design_mention_notification_content import DesignMentionNotificationContent
    from ..models.folder_access_requested_notification_content import FolderAccessRequestedNotificationContent
    from ..models.share_design_notification_content import ShareDesignNotificationContent
    from ..models.share_folder_notification_content import ShareFolderNotificationContent
    from ..models.suggestion_notification_content import SuggestionNotificationContent
    from ..models.team_invite_notification_content import TeamInviteNotificationContent


T = TypeVar("T", bound="Notification")


@_attrs_define
class Notification:
    """
    Attributes:
        id (str): The unique identifier for the notification. Example: eb595730.
        created_at (int): When the notification was created, as a UNIX timestamp (in seconds
            since the UNIX epoch). Example: 1377396000.
        content (CommentNotificationContent | DesignAccessRequestedNotificationContent |
            DesignApprovalRequestedNotificationContent | DesignApprovalResponseNotificationContent |
            DesignApprovalReviewerInvalidatedNotificationContent | DesignMentionNotificationContent |
            FolderAccessRequestedNotificationContent | ShareDesignNotificationContent | ShareFolderNotificationContent |
            SuggestionNotificationContent | TeamInviteNotificationContent): The notification content object, which contains
            metadata about the event.
    """

    id: str
    created_at: int
    content: (
        CommentNotificationContent
        | DesignAccessRequestedNotificationContent
        | DesignApprovalRequestedNotificationContent
        | DesignApprovalResponseNotificationContent
        | DesignApprovalReviewerInvalidatedNotificationContent
        | DesignMentionNotificationContent
        | FolderAccessRequestedNotificationContent
        | ShareDesignNotificationContent
        | ShareFolderNotificationContent
        | SuggestionNotificationContent
        | TeamInviteNotificationContent
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.comment_notification_content import CommentNotificationContent
        from ..models.design_access_requested_notification_content import DesignAccessRequestedNotificationContent
        from ..models.design_approval_requested_notification_content import DesignApprovalRequestedNotificationContent
        from ..models.design_approval_response_notification_content import DesignApprovalResponseNotificationContent
        from ..models.design_approval_reviewer_invalidated_notification_content import (
            DesignApprovalReviewerInvalidatedNotificationContent,
        )
        from ..models.design_mention_notification_content import DesignMentionNotificationContent
        from ..models.folder_access_requested_notification_content import FolderAccessRequestedNotificationContent
        from ..models.share_design_notification_content import ShareDesignNotificationContent
        from ..models.share_folder_notification_content import ShareFolderNotificationContent
        from ..models.team_invite_notification_content import TeamInviteNotificationContent

        id = self.id

        created_at = self.created_at

        content: dict[str, Any]
        if isinstance(self.content, ShareDesignNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, ShareFolderNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, CommentNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, DesignAccessRequestedNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, DesignApprovalRequestedNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, DesignApprovalResponseNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, DesignApprovalReviewerInvalidatedNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, DesignMentionNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, TeamInviteNotificationContent):
            content = self.content.to_dict()
        elif isinstance(self.content, FolderAccessRequestedNotificationContent):
            content = self.content.to_dict()
        else:
            content = self.content.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "created_at": created_at,
                "content": content,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.comment_notification_content import CommentNotificationContent
        from ..models.design_access_requested_notification_content import DesignAccessRequestedNotificationContent
        from ..models.design_approval_requested_notification_content import DesignApprovalRequestedNotificationContent
        from ..models.design_approval_response_notification_content import DesignApprovalResponseNotificationContent
        from ..models.design_approval_reviewer_invalidated_notification_content import (
            DesignApprovalReviewerInvalidatedNotificationContent,
        )
        from ..models.design_mention_notification_content import DesignMentionNotificationContent
        from ..models.folder_access_requested_notification_content import FolderAccessRequestedNotificationContent
        from ..models.share_design_notification_content import ShareDesignNotificationContent
        from ..models.share_folder_notification_content import ShareFolderNotificationContent
        from ..models.suggestion_notification_content import SuggestionNotificationContent
        from ..models.team_invite_notification_content import TeamInviteNotificationContent

        d = dict(src_dict)
        id = d.pop("id")

        created_at = d.pop("created_at")

        def _parse_content(
            data: object,
        ) -> (
            CommentNotificationContent
            | DesignAccessRequestedNotificationContent
            | DesignApprovalRequestedNotificationContent
            | DesignApprovalResponseNotificationContent
            | DesignApprovalReviewerInvalidatedNotificationContent
            | DesignMentionNotificationContent
            | FolderAccessRequestedNotificationContent
            | ShareDesignNotificationContent
            | ShareFolderNotificationContent
            | SuggestionNotificationContent
            | TeamInviteNotificationContent
        ):
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_0 = ShareDesignNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_1 = ShareFolderNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_2 = CommentNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_3 = DesignAccessRequestedNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_3
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_4 = DesignApprovalRequestedNotificationContent.from_dict(
                    data
                )

                return componentsschemas_notification_content_type_4
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_5 = DesignApprovalResponseNotificationContent.from_dict(
                    data
                )

                return componentsschemas_notification_content_type_5
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_6 = (
                    DesignApprovalReviewerInvalidatedNotificationContent.from_dict(data)
                )

                return componentsschemas_notification_content_type_6
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_7 = DesignMentionNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_7
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_8 = TeamInviteNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_8
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_notification_content_type_9 = FolderAccessRequestedNotificationContent.from_dict(data)

                return componentsschemas_notification_content_type_9
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_notification_content_type_10 = SuggestionNotificationContent.from_dict(data)

            return componentsschemas_notification_content_type_10

        content = _parse_content(d.pop("content"))

        notification = cls(
            id=id,
            created_at=created_at,
            content=content,
        )

        notification.additional_properties = d
        return notification

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
