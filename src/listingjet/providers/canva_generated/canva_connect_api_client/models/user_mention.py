from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.team_user import TeamUser


T = TypeVar("T", bound="UserMention")


@_attrs_define
class UserMention:
    """Information about the user mentioned in a comment thread or reply. Each user mention is keyed using the user's user
    ID and team ID separated by a colon (`user_id:team_id`).

        Attributes:
            tag (str): The mention tag for the user mentioned in the comment thread or reply content. This has the format of
                the user's user ID and team ID separated by a colon (`user_id:team_id`). Example:
                oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP.
            user (TeamUser): Metadata for the user, consisting of the User ID, Team ID, and display name.
    """

    tag: str
    user: TeamUser
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        tag = self.tag

        user = self.user.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "tag": tag,
                "user": user,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.team_user import TeamUser

        d = dict(src_dict)
        tag = d.pop("tag")

        user = TeamUser.from_dict(d.pop("user"))

        user_mention = cls(
            tag=tag,
            user=user,
        )

        user_mention.additional_properties = d
        return user_mention

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
