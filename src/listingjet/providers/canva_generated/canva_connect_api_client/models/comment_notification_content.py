from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.comment_notification_content_type import CommentNotificationContentType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.assigned_comment_event import AssignedCommentEvent
    from ..models.comment_event_deprecated import CommentEventDeprecated
    from ..models.design_summary import DesignSummary
    from ..models.mention_comment_event import MentionCommentEvent
    from ..models.new_comment_event import NewCommentEvent
    from ..models.reply_comment_event import ReplyCommentEvent
    from ..models.resolved_comment_event import ResolvedCommentEvent
    from ..models.team_user import TeamUser
    from ..models.user import User


T = TypeVar("T", bound="CommentNotificationContent")


@_attrs_define
class CommentNotificationContent:
    """The notification content for when someone comments on a design.

    Attributes:
        type_ (CommentNotificationContentType):  Example: comment.
        triggering_user (User): Metadata for the user, consisting of the User ID and display name.
        receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
        design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
        comment_url (str | Unset): A URL to the design, focused on the new comment.

            The `comment_url` property is deprecated.
            For details of the comment event, use the `comment_event` property instead. Example:
            https://www.canva.com/design/3WCduQdjayTcPVM/z128cqanFu7E3/edit?ui=OdllGgZ4Snnq3MD8uI10bfA.
        comment (CommentEventDeprecated | Unset): Basic details about the comment.

            The `comment` property is deprecated.
            For details of the comment event, use the `comment_event` property instead.
        comment_event (AssignedCommentEvent | MentionCommentEvent | NewCommentEvent | ReplyCommentEvent |
            ResolvedCommentEvent | Unset): The type of comment event, including additional type-specific properties.
    """

    type_: CommentNotificationContentType
    triggering_user: User
    receiving_team_user: TeamUser
    design: DesignSummary
    comment_url: str | Unset = UNSET
    comment: CommentEventDeprecated | Unset = UNSET
    comment_event: (
        AssignedCommentEvent | MentionCommentEvent | NewCommentEvent | ReplyCommentEvent | ResolvedCommentEvent | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.assigned_comment_event import AssignedCommentEvent
        from ..models.new_comment_event import NewCommentEvent
        from ..models.reply_comment_event import ReplyCommentEvent
        from ..models.resolved_comment_event import ResolvedCommentEvent

        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        design = self.design.to_dict()

        comment_url = self.comment_url

        comment: dict[str, Any] | Unset = UNSET
        if not isinstance(self.comment, Unset):
            comment = self.comment.to_dict()

        comment_event: dict[str, Any] | Unset
        if isinstance(self.comment_event, Unset):
            comment_event = UNSET
        elif isinstance(self.comment_event, NewCommentEvent):
            comment_event = self.comment_event.to_dict()
        elif isinstance(self.comment_event, AssignedCommentEvent):
            comment_event = self.comment_event.to_dict()
        elif isinstance(self.comment_event, ResolvedCommentEvent):
            comment_event = self.comment_event.to_dict()
        elif isinstance(self.comment_event, ReplyCommentEvent):
            comment_event = self.comment_event.to_dict()
        else:
            comment_event = self.comment_event.to_dict()

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
        if comment_url is not UNSET:
            field_dict["comment_url"] = comment_url
        if comment is not UNSET:
            field_dict["comment"] = comment
        if comment_event is not UNSET:
            field_dict["comment_event"] = comment_event

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.assigned_comment_event import AssignedCommentEvent
        from ..models.comment_event_deprecated import CommentEventDeprecated
        from ..models.design_summary import DesignSummary
        from ..models.mention_comment_event import MentionCommentEvent
        from ..models.new_comment_event import NewCommentEvent
        from ..models.reply_comment_event import ReplyCommentEvent
        from ..models.resolved_comment_event import ResolvedCommentEvent
        from ..models.team_user import TeamUser
        from ..models.user import User

        d = dict(src_dict)
        type_ = CommentNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        design = DesignSummary.from_dict(d.pop("design"))

        comment_url = d.pop("comment_url", UNSET)

        _comment = d.pop("comment", UNSET)
        comment: CommentEventDeprecated | Unset
        if isinstance(_comment, Unset):
            comment = UNSET
        else:
            comment = CommentEventDeprecated.from_dict(_comment)

        def _parse_comment_event(
            data: object,
        ) -> (
            AssignedCommentEvent
            | MentionCommentEvent
            | NewCommentEvent
            | ReplyCommentEvent
            | ResolvedCommentEvent
            | Unset
        ):
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_comment_event_type_0 = NewCommentEvent.from_dict(data)

                return componentsschemas_comment_event_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_comment_event_type_1 = AssignedCommentEvent.from_dict(data)

                return componentsschemas_comment_event_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_comment_event_type_2 = ResolvedCommentEvent.from_dict(data)

                return componentsschemas_comment_event_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_comment_event_type_3 = ReplyCommentEvent.from_dict(data)

                return componentsschemas_comment_event_type_3
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_comment_event_type_4 = MentionCommentEvent.from_dict(data)

            return componentsschemas_comment_event_type_4

        comment_event = _parse_comment_event(d.pop("comment_event", UNSET))

        comment_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            design=design,
            comment_url=comment_url,
            comment=comment,
            comment_event=comment_event,
        )

        comment_notification_content.additional_properties = d
        return comment_notification_content

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
