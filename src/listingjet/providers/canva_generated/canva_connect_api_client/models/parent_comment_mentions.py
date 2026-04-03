from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.team_user import TeamUser


T = TypeVar("T", bound="ParentCommentMentions")


@_attrs_define
class ParentCommentMentions:
    """The Canva users mentioned in the comment.

    Example:
        {'oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP': {'user_id': 'oUnPjZ2k2yuhftbWF7873o', 'team_id':
            'oBpVhLW22VrqtwKgaayRbP', 'display_name': 'John Doe'}}

    """

    additional_properties: dict[str, TeamUser] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            field_dict[prop_name] = prop.to_dict()

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.team_user import TeamUser

        d = dict(src_dict)
        parent_comment_mentions = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():
            additional_property = TeamUser.from_dict(prop_dict)

            additional_properties[prop_name] = additional_property

        parent_comment_mentions.additional_properties = additional_properties
        return parent_comment_mentions

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> TeamUser:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: TeamUser) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
