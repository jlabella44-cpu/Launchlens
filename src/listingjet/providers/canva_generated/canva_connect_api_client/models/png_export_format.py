from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.export_quality import ExportQuality
from ..models.png_export_format_type import PngExportFormatType
from ..types import UNSET, Unset

T = TypeVar("T", bound="PngExportFormat")


@_attrs_define
class PngExportFormat:
    """Export the design as a PNG. Height or width (or both) may be specified, otherwise
    the file will be exported at it's default size. You may also specify whether to export the
    file losslessly, and whether to export a multi-page design as a single image.

    If the user is on the Canva Free plan, the export height and width for a fixed-dimension design can't be upscaled by
    more than a factor of `1.125`.

        Attributes:
            type_ (PngExportFormatType):
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
            lossless (bool | Unset): If set to `true` (default), the PNG is exported without compression.

                If set to `false`, the PNG is compressed using a lossy compression algorithm.

                AVAILABILITY: Lossy PNG compression is only available to users on a Canva plan that has premium features, such
                as Canva Pro. If the user is on the Canva Free plan and this parameter is set to `false`, the export operation
                will fail. Default: True.
            transparent_background (bool | Unset): If set to `true`, the PNG is exported with a transparent background.

                AVAILABILITY: This option is only available to users on a Canva plan that has premium features, such as Canva
                Pro. If the user is on the Canva Free plan and this parameter is set to `true`, the export operation will fail.
                Default: False.
            as_single_image (bool | Unset): When `true`, multi-page designs are merged into a single image.
                When `false` (default), each page is exported as a separate image. Default: False.
            pages (list[int] | Unset): To specify which pages to export in a multi-page design, provide the page numbers as
                an array. The first page in a design is page `1`.
                If `pages` isn't specified, all the pages are exported. Example: [2, 3, 4].
    """

    type_: PngExportFormatType
    export_quality: ExportQuality | Unset = UNSET
    height: int | Unset = UNSET
    width: int | Unset = UNSET
    lossless: bool | Unset = True
    transparent_background: bool | Unset = False
    as_single_image: bool | Unset = False
    pages: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        export_quality: str | Unset = UNSET
        if not isinstance(self.export_quality, Unset):
            export_quality = self.export_quality.value

        height = self.height

        width = self.width

        lossless = self.lossless

        transparent_background = self.transparent_background

        as_single_image = self.as_single_image

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
        if export_quality is not UNSET:
            field_dict["export_quality"] = export_quality
        if height is not UNSET:
            field_dict["height"] = height
        if width is not UNSET:
            field_dict["width"] = width
        if lossless is not UNSET:
            field_dict["lossless"] = lossless
        if transparent_background is not UNSET:
            field_dict["transparent_background"] = transparent_background
        if as_single_image is not UNSET:
            field_dict["as_single_image"] = as_single_image
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = PngExportFormatType(d.pop("type"))

        _export_quality = d.pop("export_quality", UNSET)
        export_quality: ExportQuality | Unset
        if isinstance(_export_quality, Unset):
            export_quality = UNSET
        else:
            export_quality = ExportQuality(_export_quality)

        height = d.pop("height", UNSET)

        width = d.pop("width", UNSET)

        lossless = d.pop("lossless", UNSET)

        transparent_background = d.pop("transparent_background", UNSET)

        as_single_image = d.pop("as_single_image", UNSET)

        pages = cast(list[int], d.pop("pages", UNSET))

        png_export_format = cls(
            type_=type_,
            export_quality=export_quality,
            height=height,
            width=width,
            lossless=lossless,
            transparent_background=transparent_background,
            as_single_image=as_single_image,
            pages=pages,
        )

        png_export_format.additional_properties = d
        return png_export_format

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
