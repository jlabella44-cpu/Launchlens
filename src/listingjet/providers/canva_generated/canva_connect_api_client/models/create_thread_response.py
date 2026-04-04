from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.thread import Thread


T = TypeVar("T", bound="CreateThreadResponse")


@_attrs_define
class CreateThreadResponse:
    """
    Attributes:
        thread (Thread): A discussion thread on a design.

            The `type` of the thread can be found in the `thread_type` object, along with additional type-specific
            properties.
            The `author` of the thread might be missing if that user account no longer exists.
    """

    thread: Thread
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        thread = self.thread.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "thread": thread,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.thread import Thread

        d = dict(src_dict)
        thread = Thread.from_dict(d.pop("thread"))

        create_thread_response = cls(
            thread=thread,
        )

        create_thread_response.additional_properties = d
        return create_thread_response

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
