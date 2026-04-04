from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.gif_export_format import GifExportFormat
    from ..models.html_bundle_export_format import HtmlBundleExportFormat
    from ..models.html_standalone_export_format import HtmlStandaloneExportFormat
    from ..models.jpg_export_format import JpgExportFormat
    from ..models.mp_4_export_format import Mp4ExportFormat
    from ..models.pdf_export_format import PdfExportFormat
    from ..models.png_export_format import PngExportFormat
    from ..models.pptx_export_format import PptxExportFormat


T = TypeVar("T", bound="CreateDesignExportJobRequest")


@_attrs_define
class CreateDesignExportJobRequest:
    """Body parameters for starting an export job for a design.
    It must include a design ID, and one of the supported export formats.

        Example:
            {'design_id': 'DAVZr1z5464', 'format': {'type': 'pdf', 'size': 'a4', 'pages': [2, 3, 4]}}

        Attributes:
            design_id (str): The design ID.
            format_ (GifExportFormat | HtmlBundleExportFormat | HtmlStandaloneExportFormat | JpgExportFormat |
                Mp4ExportFormat | PdfExportFormat | PngExportFormat | PptxExportFormat): Details about the desired export
                format.
    """

    design_id: str
    format_: (
        GifExportFormat
        | HtmlBundleExportFormat
        | HtmlStandaloneExportFormat
        | JpgExportFormat
        | Mp4ExportFormat
        | PdfExportFormat
        | PngExportFormat
        | PptxExportFormat
    )
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.gif_export_format import GifExportFormat
        from ..models.html_bundle_export_format import HtmlBundleExportFormat
        from ..models.jpg_export_format import JpgExportFormat
        from ..models.mp_4_export_format import Mp4ExportFormat
        from ..models.pdf_export_format import PdfExportFormat
        from ..models.png_export_format import PngExportFormat
        from ..models.pptx_export_format import PptxExportFormat

        design_id = self.design_id

        format_: dict[str, Any]
        if isinstance(self.format_, PdfExportFormat):
            format_ = self.format_.to_dict()
        elif isinstance(self.format_, JpgExportFormat):
            format_ = self.format_.to_dict()
        elif isinstance(self.format_, PngExportFormat):
            format_ = self.format_.to_dict()
        elif isinstance(self.format_, PptxExportFormat):
            format_ = self.format_.to_dict()
        elif isinstance(self.format_, GifExportFormat):
            format_ = self.format_.to_dict()
        elif isinstance(self.format_, Mp4ExportFormat):
            format_ = self.format_.to_dict()
        elif isinstance(self.format_, HtmlBundleExportFormat):
            format_ = self.format_.to_dict()
        else:
            format_ = self.format_.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "design_id": design_id,
                "format": format_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.gif_export_format import GifExportFormat
        from ..models.html_bundle_export_format import HtmlBundleExportFormat
        from ..models.html_standalone_export_format import HtmlStandaloneExportFormat
        from ..models.jpg_export_format import JpgExportFormat
        from ..models.mp_4_export_format import Mp4ExportFormat
        from ..models.pdf_export_format import PdfExportFormat
        from ..models.png_export_format import PngExportFormat
        from ..models.pptx_export_format import PptxExportFormat

        d = dict(src_dict)
        design_id = d.pop("design_id")

        def _parse_format_(
            data: object,
        ) -> (
            GifExportFormat
            | HtmlBundleExportFormat
            | HtmlStandaloneExportFormat
            | JpgExportFormat
            | Mp4ExportFormat
            | PdfExportFormat
            | PngExportFormat
            | PptxExportFormat
        ):
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_0 = PdfExportFormat.from_dict(data)

                return componentsschemas_export_format_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_1 = JpgExportFormat.from_dict(data)

                return componentsschemas_export_format_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_2 = PngExportFormat.from_dict(data)

                return componentsschemas_export_format_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_3 = PptxExportFormat.from_dict(data)

                return componentsschemas_export_format_type_3
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_4 = GifExportFormat.from_dict(data)

                return componentsschemas_export_format_type_4
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_5 = Mp4ExportFormat.from_dict(data)

                return componentsschemas_export_format_type_5
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_export_format_type_6 = HtmlBundleExportFormat.from_dict(data)

                return componentsschemas_export_format_type_6
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_export_format_type_7 = HtmlStandaloneExportFormat.from_dict(data)

            return componentsschemas_export_format_type_7

        format_ = _parse_format_(d.pop("format"))

        create_design_export_job_request = cls(
            design_id=design_id,
            format_=format_,
        )

        create_design_export_job_request.additional_properties = d
        return create_design_export_job_request

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
