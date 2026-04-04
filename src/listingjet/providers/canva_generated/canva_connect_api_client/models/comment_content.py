from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CommentContent")


@_attrs_define
class CommentContent:
    """The content of a comment thread or reply.

    Attributes:
        plaintext (str): The content in plaintext.
            Any user mention tags are shown in the format `[user_id:team_id]`. Example: Great work
            [oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP]!.
        markdown (str | Unset): The content in markdown.
            Any user mention tags are shown in the format `[user_id:team_id]` Example: *_Great work_*
            [oUnPjZ2k2yuhftbWF7873o:oBpVhLW22VrqtwKgaayRbP]!.
    """

    plaintext: str
    markdown: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plaintext = self.plaintext

        markdown = self.markdown

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plaintext": plaintext,
            }
        )
        if markdown is not UNSET:
            field_dict["markdown"] = markdown

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        plaintext = d.pop("plaintext")

        markdown = d.pop("markdown", UNSET)

        comment_content = cls(
            plaintext=plaintext,
            markdown=markdown,
        )

        comment_content.additional_properties = d
        return comment_content

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
