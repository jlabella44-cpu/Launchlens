from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.export_page_size import ExportPageSize
from ..models.export_quality import ExportQuality
from ..models.pdf_export_format_type import PdfExportFormatType
from ..types import UNSET, Unset

T = TypeVar("T", bound="PdfExportFormat")


@_attrs_define
class PdfExportFormat:
    """Export the design as a PDF. Providing a paper size is optional.

    Attributes:
        type_ (PdfExportFormatType):
        export_quality (ExportQuality | Unset): Specifies the export quality of the design.
        size (ExportPageSize | Unset): The paper size of the export PDF file. The `size` attribute is only supported for
            Documents (Canva Docs). Example: a4.
        pages (list[int] | Unset): To specify which pages to export in a multi-page design, provide the page numbers as
            an array. The first page in a design is page `1`.
            If `pages` isn't specified, all the pages are exported. Example: [2, 3, 4].
    """

    type_: PdfExportFormatType
    export_quality: ExportQuality | Unset = UNSET
    size: ExportPageSize | Unset = UNSET
    pages: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        export_quality: str | Unset = UNSET
        if not isinstance(self.export_quality, Unset):
            export_quality = self.export_quality.value

        size: str | Unset = UNSET
        if not isinstance(self.size, Unset):
            size = self.size.value

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
        if size is not UNSET:
            field_dict["size"] = size
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = PdfExportFormatType(d.pop("type"))

        _export_quality = d.pop("export_quality", UNSET)
        export_quality: ExportQuality | Unset
        if isinstance(_export_quality, Unset):
            export_quality = UNSET
        else:
            export_quality = ExportQuality(_export_quality)

        _size = d.pop("size", UNSET)
        size: ExportPageSize | Unset
        if isinstance(_size, Unset):
            size = UNSET
        else:
            size = ExportPageSize(_size)

        pages = cast(list[int], d.pop("pages", UNSET))

        pdf_export_format = cls(
            type_=type_,
            export_quality=export_quality,
            size=size,
            pages=pages,
        )

        pdf_export_format.additional_properties = d
        return pdf_export_format

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
