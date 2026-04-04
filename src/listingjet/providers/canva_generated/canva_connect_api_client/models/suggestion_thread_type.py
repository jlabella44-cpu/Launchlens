from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.suggestion_status import SuggestionStatus
from ..models.suggestion_thread_type_type import SuggestionThreadTypeType

if TYPE_CHECKING:
    from ..models.add_suggested_edit import AddSuggestedEdit
    from ..models.delete_suggested_edit import DeleteSuggestedEdit
    from ..models.format_suggested_edit import FormatSuggestedEdit


T = TypeVar("T", bound="SuggestionThreadType")


@_attrs_define
class SuggestionThreadType:
    """A suggestion thread.

    Attributes:
        type_ (SuggestionThreadTypeType):
        suggested_edits (list[AddSuggestedEdit | DeleteSuggestedEdit | FormatSuggestedEdit]):
        status (SuggestionStatus): The current status of the suggestion.
    """

    type_: SuggestionThreadTypeType
    suggested_edits: list[AddSuggestedEdit | DeleteSuggestedEdit | FormatSuggestedEdit]
    status: SuggestionStatus
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.add_suggested_edit import AddSuggestedEdit
        from ..models.delete_suggested_edit import DeleteSuggestedEdit

        type_ = self.type_.value

        suggested_edits = []
        for suggested_edits_item_data in self.suggested_edits:
            suggested_edits_item: dict[str, Any]
            if isinstance(suggested_edits_item_data, AddSuggestedEdit):
                suggested_edits_item = suggested_edits_item_data.to_dict()
            elif isinstance(suggested_edits_item_data, DeleteSuggestedEdit):
                suggested_edits_item = suggested_edits_item_data.to_dict()
            else:
                suggested_edits_item = suggested_edits_item_data.to_dict()

            suggested_edits.append(suggested_edits_item)

        status = self.status.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "suggested_edits": suggested_edits,
                "status": status,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.add_suggested_edit import AddSuggestedEdit
        from ..models.delete_suggested_edit import DeleteSuggestedEdit
        from ..models.format_suggested_edit import FormatSuggestedEdit

        d = dict(src_dict)
        type_ = SuggestionThreadTypeType(d.pop("type"))

        suggested_edits = []
        _suggested_edits = d.pop("suggested_edits")
        for suggested_edits_item_data in _suggested_edits:

            def _parse_suggested_edits_item(
                data: object,
            ) -> AddSuggestedEdit | DeleteSuggestedEdit | FormatSuggestedEdit:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_suggested_edit_type_0 = AddSuggestedEdit.from_dict(data)

                    return componentsschemas_suggested_edit_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    componentsschemas_suggested_edit_type_1 = DeleteSuggestedEdit.from_dict(data)

                    return componentsschemas_suggested_edit_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_suggested_edit_type_2 = FormatSuggestedEdit.from_dict(data)

                return componentsschemas_suggested_edit_type_2

            suggested_edits_item = _parse_suggested_edits_item(suggested_edits_item_data)

            suggested_edits.append(suggested_edits_item)

        status = SuggestionStatus(d.pop("status"))

        suggestion_thread_type = cls(
            type_=type_,
            suggested_edits=suggested_edits,
            status=status,
        )

        suggestion_thread_type.additional_properties = d
        return suggestion_thread_type

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
