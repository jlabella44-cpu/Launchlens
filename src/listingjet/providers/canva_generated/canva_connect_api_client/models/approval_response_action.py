from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ApprovalResponseAction")


@_attrs_define
class ApprovalResponseAction:
    """Metadata about the design approval response.

    Attributes:
        approved (bool): Whether the design was approved. When `true`, the reviewer has approved
            the design.
        ready_to_publish (bool | Unset): Whether the design is ready to publish. When `true`, the design has been
            approved
            by all reviewers and can be published.
        message (str | Unset): The message included by a user responding to a design approval request.
    """

    approved: bool
    ready_to_publish: bool | Unset = UNSET
    message: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        approved = self.approved

        ready_to_publish = self.ready_to_publish

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "approved": approved,
            }
        )
        if ready_to_publish is not UNSET:
            field_dict["ready_to_publish"] = ready_to_publish
        if message is not UNSET:
            field_dict["message"] = message

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        approved = d.pop("approved")

        ready_to_publish = d.pop("ready_to_publish", UNSET)

        message = d.pop("message", UNSET)

        approval_response_action = cls(
            approved=approved,
            ready_to_publish=ready_to_publish,
            message=message,
        )

        approval_response_action.additional_properties = d
        return approval_response_action

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
