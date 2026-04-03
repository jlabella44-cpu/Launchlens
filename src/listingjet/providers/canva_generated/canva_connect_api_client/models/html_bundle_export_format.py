from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.html_bundle_export_format_type import HtmlBundleExportFormatType
from ..types import UNSET, Unset

T = TypeVar("T", bound="HtmlBundleExportFormat")


@_attrs_define
class HtmlBundleExportFormat:
    """Export the email design as an HTML bundle. An HTML bundle is a zip file that contains an HTML file and the
    associated assets.

        Attributes:
            type_ (HtmlBundleExportFormatType):
            pages (list[int] | Unset): The pages of the design to export. Currently only a single page can be exported. If
                not provided,
                the first page of the design is used. Example: [1].
    """

    type_: HtmlBundleExportFormatType
    pages: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        pages: list[int] | Unset = UNSET
        if not isinstance(self.pages, Unset):
            pages = self.pages

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
            }
        )
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = HtmlBundleExportFormatType(d.pop("type"))

        pages = cast(list[int], d.pop("pages", UNSET))

        html_bundle_export_format = cls(
            type_=type_,
            pages=pages,
        )

        html_bundle_export_format.additional_properties = d
        return html_bundle_export_format

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
