from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.rejected_suggestion_event_type_type import RejectedSuggestionEventTypeType

if TYPE_CHECKING:
    from ..models.thread import Thread


T = TypeVar("T", bound="RejectedSuggestionEventType")


@_attrs_define
class RejectedSuggestionEventType:
    """Event type for a suggestion that has been rejected.

    Attributes:
        type_ (RejectedSuggestionEventTypeType):
        suggestion_url (str): A URL to the design, focused on the suggestion. Example:
            https://www.canva.com/design/3WCduQdjayTcPVM/z128cqanFu7E3/edit?ui=OdllGgZ4Snnq3MD8uI10bfA.
        suggestion (Thread): A discussion thread on a design.

            The `type` of the thread can be found in the `thread_type` object, along with additional type-specific
            properties.
            The `author` of the thread might be missing if that user account no longer exists.
    """

    type_: RejectedSuggestionEventTypeType
    suggestion_url: str
    suggestion: Thread
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        suggestion_url = self.suggestion_url

        suggestion = self.suggestion.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "suggestion_url": suggestion_url,
                "suggestion": suggestion,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.thread import Thread

        d = dict(src_dict)
        type_ = RejectedSuggestionEventTypeType(d.pop("type"))

        suggestion_url = d.pop("suggestion_url")

        suggestion = Thread.from_dict(d.pop("suggestion"))

        rejected_suggestion_event_type = cls(
            type_=type_,
            suggestion_url=suggestion_url,
            suggestion=suggestion,
        )

        rejected_suggestion_event_type.additional_properties = d
        return rejected_suggestion_event_type

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
