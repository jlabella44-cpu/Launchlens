from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="TrialInformation")


@_attrs_define
class TrialInformation:
    """WARNING: Trials and trial information are a [preview feature](https://www.canva.dev/docs/connect/#preview-apis).
    There might be unannounced breaking changes to this feature which won't produce a new API version.

        Attributes:
            uses_remaining (int): The number of uses remaining in the free trial.
            upgrade_url (str): The URL for a user to upgrade their Canva account. Example:
                https://www.canva.com/?tailoringUpsellDialog=GENERIC_C4W.
    """

    uses_remaining: int
    upgrade_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uses_remaining = self.uses_remaining

        upgrade_url = self.upgrade_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "uses_remaining": uses_remaining,
                "upgrade_url": upgrade_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        uses_remaining = d.pop("uses_remaining")

        upgrade_url = d.pop("upgrade_url")

        trial_information = cls(
            uses_remaining=uses_remaining,
            upgrade_url=upgrade_url,
        )

        trial_information.additional_properties = d
        return trial_information

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
