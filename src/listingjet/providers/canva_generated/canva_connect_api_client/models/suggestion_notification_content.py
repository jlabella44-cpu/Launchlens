from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.suggestion_notification_content_type import SuggestionNotificationContentType

if TYPE_CHECKING:
    from ..models.accepted_suggestion_event_type import AcceptedSuggestionEventType
    from ..models.design_summary import DesignSummary
    from ..models.mention_suggestion_event_type import MentionSuggestionEventType
    from ..models.new_suggestion_event_type import NewSuggestionEventType
    from ..models.rejected_suggestion_event_type import RejectedSuggestionEventType
    from ..models.reply_suggestion_event_type import ReplySuggestionEventType
    from ..models.team_user import TeamUser
    from ..models.user import User


T = TypeVar("T", bound="SuggestionNotificationContent")


@_attrs_define
class SuggestionNotificationContent:
    """The notification content when someone does one of the following actions:

    - Suggests edits to a design.
    - Applies or rejects a suggestion.
    - Replies to a suggestion.
    - Mentions a user in a reply to a suggestion.

       Attributes:
           type_ (SuggestionNotificationContentType):
           triggering_user (User): Metadata for the user, consisting of the User ID and display name.
           receiving_team_user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
           design (DesignSummary): Basic details about the design, such as the design's ID, title, and URL.
           suggestion_event_type (AcceptedSuggestionEventType | MentionSuggestionEventType | NewSuggestionEventType |
               RejectedSuggestionEventType | ReplySuggestionEventType): The type of suggestion event, along with additional
               type-specific properties.
    """

    type_: SuggestionNotificationContentType
    triggering_user: User
    receiving_team_user: TeamUser
    design: DesignSummary
    suggestion_event_type: (
        AcceptedSuggestionEventType
        | MentionSuggestionEventType
        | NewSuggestionEventType
        | RejectedSuggestionEventType
        | ReplySuggestionEventType
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.accepted_suggestion_event_type import AcceptedSuggestionEventType
        from ..models.new_suggestion_event_type import NewSuggestionEventType
        from ..models.rejected_suggestion_event_type import RejectedSuggestionEventType
        from ..models.reply_suggestion_event_type import ReplySuggestionEventType

        type_ = self.type_.value

        triggering_user = self.triggering_user.to_dict()

        receiving_team_user = self.receiving_team_user.to_dict()

        design = self.design.to_dict()

        suggestion_event_type: dict[str, Any]
        if isinstance(self.suggestion_event_type, NewSuggestionEventType):
            suggestion_event_type = self.suggestion_event_type.to_dict()
        elif isinstance(self.suggestion_event_type, AcceptedSuggestionEventType):
            suggestion_event_type = self.suggestion_event_type.to_dict()
        elif isinstance(self.suggestion_event_type, RejectedSuggestionEventType):
            suggestion_event_type = self.suggestion_event_type.to_dict()
        elif isinstance(self.suggestion_event_type, ReplySuggestionEventType):
            suggestion_event_type = self.suggestion_event_type.to_dict()
        else:
            suggestion_event_type = self.suggestion_event_type.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "triggering_user": triggering_user,
                "receiving_team_user": receiving_team_user,
                "design": design,
                "suggestion_event_type": suggestion_event_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.accepted_suggestion_event_type import AcceptedSuggestionEventType
        from ..models.design_summary import DesignSummary
        from ..models.mention_suggestion_event_type import MentionSuggestionEventType
        from ..models.new_suggestion_event_type import NewSuggestionEventType
        from ..models.rejected_suggestion_event_type import RejectedSuggestionEventType
        from ..models.reply_suggestion_event_type import ReplySuggestionEventType
        from ..models.team_user import TeamUser
        from ..models.user import User

        d = dict(src_dict)
        type_ = SuggestionNotificationContentType(d.pop("type"))

        triggering_user = User.from_dict(d.pop("triggering_user"))

        receiving_team_user = TeamUser.from_dict(d.pop("receiving_team_user"))

        design = DesignSummary.from_dict(d.pop("design"))

        def _parse_suggestion_event_type(
            data: object,
        ) -> (
            AcceptedSuggestionEventType
            | MentionSuggestionEventType
            | NewSuggestionEventType
            | RejectedSuggestionEventType
            | ReplySuggestionEventType
        ):
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_suggestion_event_type_type_0 = NewSuggestionEventType.from_dict(data)

                return componentsschemas_suggestion_event_type_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_suggestion_event_type_type_1 = AcceptedSuggestionEventType.from_dict(data)

                return componentsschemas_suggestion_event_type_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_suggestion_event_type_type_2 = RejectedSuggestionEventType.from_dict(data)

                return componentsschemas_suggestion_event_type_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_suggestion_event_type_type_3 = ReplySuggestionEventType.from_dict(data)

                return componentsschemas_suggestion_event_type_type_3
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_suggestion_event_type_type_4 = MentionSuggestionEventType.from_dict(data)

            return componentsschemas_suggestion_event_type_type_4

        suggestion_event_type = _parse_suggestion_event_type(d.pop("suggestion_event_type"))

        suggestion_notification_content = cls(
            type_=type_,
            triggering_user=triggering_user,
            receiving_team_user=receiving_team_user,
            design=design,
            suggestion_event_type=suggestion_event_type,
        )

        suggestion_notification_content.additional_properties = d
        return suggestion_notification_content

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
