from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.export_quality import ExportQuality
from ..models.jpg_export_format_type import JpgExportFormatType
from ..types import UNSET, Unset

T = TypeVar("T", bound="JpgExportFormat")


@_attrs_define
class JpgExportFormat:
    """Export the design as a JPEG. Compression quality must be provided. Height or width (or both)
    may be specified, otherwise the file will be exported at it's default size.

    If the user is on the Canva Free plan, the export height and width for a fixed-dimension design can't be upscaled by
    more than a factor of `1.125`.

        Attributes:
            type_ (JpgExportFormatType):
            quality (int): For the `jpg` type, the `quality` of the exported JPEG determines how compressed the exported
                file should be. A _low_ `quality` value will create a file with a smaller file size, but the resulting file will
                have pixelated artifacts when compared to a file created with a _high_ `quality` value. Example: 80.
            export_quality (ExportQuality | Unset): Specifies the export quality of the design.
            height (int | Unset): Specify the height in pixels of the exported image. Note the following behavior:

                - If no height or width is specified, the image is exported using the dimensions of the design.
                - If only one of height or width is specified, then the image is scaled to match that dimension, respecting the
                design's aspect ratio.
                - If both the height and width are specified, but the values don't match the design's aspect ratio, the export
                defaults to the larger dimension. Example: 400.
            width (int | Unset): Specify the width in pixels of the exported image. Note the following behavior:

                - If no width or height is specified, the image is exported using the dimensions of the design.
                - If only one of width or height is specified, then the image is scaled to match that dimension, respecting the
                design's aspect ratio.
                - If both the width and height are specified, but the values don't match the design's aspect ratio, the export
                defaults to the larger dimension. Example: 400.
            pages (list[int] | Unset): To specify which pages to export in a multi-page design, provide the page numbers as
                an array. The first page in a design is page `1`.
                If `pages` isn't specified, all the pages are exported. Example: [2, 3, 4].
    """

    type_: JpgExportFormatType
    quality: int
    export_quality: ExportQuality | Unset = UNSET
    height: int | Unset = UNSET
    width: int | Unset = UNSET
    pages: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        quality = self.quality

        export_quality: str | Unset = UNSET
        if not isinstance(self.export_quality, Unset):
            export_quality = self.export_quality.value

        height = self.height

        width = self.width

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
        if height is not UNSET:
            field_dict["height"] = height
        if width is not UNSET:
            field_dict["width"] = width
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = JpgExportFormatType(d.pop("type"))

        quality = d.pop("quality")

        _export_quality = d.pop("export_quality", UNSET)
        export_quality: ExportQuality | Unset
        if isinstance(_export_quality, Unset):
            export_quality = UNSET
        else:
            export_quality = ExportQuality(_export_quality)

        height = d.pop("height", UNSET)

        width = d.pop("width", UNSET)

        pages = cast(list[int], d.pop("pages", UNSET))

        jpg_export_format = cls(
            type_=type_,
            quality=quality,
            export_quality=export_quality,
            height=height,
            width=width,
            pages=pages,
        )

        jpg_export_format.additional_properties = d
        return jpg_export_format

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
