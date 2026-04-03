from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.export_quality import ExportQuality
from ..models.mp_4_export_format_type import Mp4ExportFormatType
from ..models.mp_4_export_quality import Mp4ExportQuality
from ..types import UNSET, Unset

T = TypeVar("T", bound="Mp4ExportFormat")


@_attrs_define
class Mp4ExportFormat:
    """Export the design as an MP4. You must specify the quality of the exported video.

    Attributes:
        type_ (Mp4ExportFormatType):
        quality (Mp4ExportQuality): The orientation and resolution of the exported video. Orientation is either
            `horizontal` or
            `vertical`, and resolution is one of `480p`, `720p`, `1080p` or `4k`.
        export_quality (ExportQuality | Unset): Specifies the export quality of the design.
        pages (list[int] | Unset): To specify which pages to export in a multi-page design, provide the page numbers as
            an array. The first page in a design is page `1`.
            If `pages` isn't specified, all the pages are exported. Example: [2, 3, 4].
    """

    type_: Mp4ExportFormatType
    quality: Mp4ExportQuality
    export_quality: ExportQuality | Unset = UNSET
    pages: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        quality = self.quality.value

        export_quality: str | Unset = UNSET
        if not isinstance(self.export_quality, Unset):
            export_quality = self.export_quality.value

        pages: list[int] | Unset = UNSET
        if not isinstance(self.pages, Unset):
            pages = self.pages

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "quality": quality,
            }
        )
        if export_quality is not UNSET:
            field_dict["export_quality"] = export_quality
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = Mp4ExportFormatType(d.pop("type"))

        quality = Mp4ExportQuality(d.pop("quality"))

        _export_quality = d.pop("export_quality", UNSET)
        export_quality: ExportQuality | Unset
        if isinstance(_export_quality, Unset):
            export_quality = UNSET
        else:
            export_quality = ExportQuality(_export_quality)

        pages = cast(list[int], d.pop("pages", UNSET))

        mp_4_export_format = cls(
            type_=type_,
            quality=quality,
            export_quality=export_quality,
            pages=pages,
        )

        mp_4_export_format.additional_properties = d
        return mp_4_export_format

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
