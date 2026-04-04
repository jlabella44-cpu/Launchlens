from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.gif_export_format_option import GifExportFormatOption
    from ..models.html_bundle_export_format_option import HtmlBundleExportFormatOption
    from ..models.html_standalone_export_format_option import HtmlStandaloneExportFormatOption
    from ..models.jpg_export_format_option import JpgExportFormatOption
    from ..models.mp_4_export_format_option import Mp4ExportFormatOption
    from ..models.pdf_export_format_option import PdfExportFormatOption
    from ..models.png_export_format_option import PngExportFormatOption
    from ..models.pptx_export_format_option import PptxExportFormatOption
    from ..models.svg_export_format_option import SvgExportFormatOption


T = TypeVar("T", bound="ExportFormatOptions")


@_attrs_define
class ExportFormatOptions:
    """The available file formats for exporting the design.

    Attributes:
        pdf (PdfExportFormatOption | Unset): Whether the design can be exported as a PDF.
        jpg (JpgExportFormatOption | Unset): Whether the design can be exported as a JPEG.
        png (PngExportFormatOption | Unset): Whether the design can be exported as a PNG.
        svg (SvgExportFormatOption | Unset): Whether the design can be exported as an SVG.
        pptx (PptxExportFormatOption | Unset): Whether the design can be exported as a PPTX.
        gif (GifExportFormatOption | Unset): Whether the design can be exported as a GIF.
        mp4 (Mp4ExportFormatOption | Unset): Whether the design can be exported as an MP4.
        html_bundle (HtmlBundleExportFormatOption | Unset): Whether the design can be exported as an HTML bundle.
        html_standalone (HtmlStandaloneExportFormatOption | Unset): Whether the design can be exported as an standalone
            HTML file.
    """

    pdf: PdfExportFormatOption | Unset = UNSET
    jpg: JpgExportFormatOption | Unset = UNSET
    png: PngExportFormatOption | Unset = UNSET
    svg: SvgExportFormatOption | Unset = UNSET
    pptx: PptxExportFormatOption | Unset = UNSET
    gif: GifExportFormatOption | Unset = UNSET
    mp4: Mp4ExportFormatOption | Unset = UNSET
    html_bundle: HtmlBundleExportFormatOption | Unset = UNSET
    html_standalone: HtmlStandaloneExportFormatOption | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        pdf: dict[str, Any] | Unset = UNSET
        if not isinstance(self.pdf, Unset):
            pdf = self.pdf.to_dict()

        jpg: dict[str, Any] | Unset = UNSET
        if not isinstance(self.jpg, Unset):
            jpg = self.jpg.to_dict()

        png: dict[str, Any] | Unset = UNSET
        if not isinstance(self.png, Unset):
            png = self.png.to_dict()

        svg: dict[str, Any] | Unset = UNSET
        if not isinstance(self.svg, Unset):
            svg = self.svg.to_dict()

        pptx: dict[str, Any] | Unset = UNSET
        if not isinstance(self.pptx, Unset):
            pptx = self.pptx.to_dict()

        gif: dict[str, Any] | Unset = UNSET
        if not isinstance(self.gif, Unset):
            gif = self.gif.to_dict()

        mp4: dict[str, Any] | Unset = UNSET
        if not isinstance(self.mp4, Unset):
            mp4 = self.mp4.to_dict()

        html_bundle: dict[str, Any] | Unset = UNSET
        if not isinstance(self.html_bundle, Unset):
            html_bundle = self.html_bundle.to_dict()

        html_standalone: dict[str, Any] | Unset = UNSET
        if not isinstance(self.html_standalone, Unset):
            html_standalone = self.html_standalone.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if pdf is not UNSET:
            field_dict["pdf"] = pdf
        if jpg is not UNSET:
            field_dict["jpg"] = jpg
        if png is not UNSET:
            field_dict["png"] = png
        if svg is not UNSET:
            field_dict["svg"] = svg
        if pptx is not UNSET:
            field_dict["pptx"] = pptx
        if gif is not UNSET:
            field_dict["gif"] = gif
        if mp4 is not UNSET:
            field_dict["mp4"] = mp4
        if html_bundle is not UNSET:
            field_dict["html_bundle"] = html_bundle
        if html_standalone is not UNSET:
            field_dict["html_standalone"] = html_standalone

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.gif_export_format_option import GifExportFormatOption
        from ..models.html_bundle_export_format_option import HtmlBundleExportFormatOption
        from ..models.html_standalone_export_format_option import HtmlStandaloneExportFormatOption
        from ..models.jpg_export_format_option import JpgExportFormatOption
        from ..models.mp_4_export_format_option import Mp4ExportFormatOption
        from ..models.pdf_export_format_option import PdfExportFormatOption
        from ..models.png_export_format_option import PngExportFormatOption
        from ..models.pptx_export_format_option import PptxExportFormatOption
        from ..models.svg_export_format_option import SvgExportFormatOption

        d = dict(src_dict)
        _pdf = d.pop("pdf", UNSET)
        pdf: PdfExportFormatOption | Unset
        if isinstance(_pdf, Unset):
            pdf = UNSET
        else:
            pdf = PdfExportFormatOption.from_dict(_pdf)

        _jpg = d.pop("jpg", UNSET)
        jpg: JpgExportFormatOption | Unset
        if isinstance(_jpg, Unset):
            jpg = UNSET
        else:
            jpg = JpgExportFormatOption.from_dict(_jpg)

        _png = d.pop("png", UNSET)
        png: PngExportFormatOption | Unset
        if isinstance(_png, Unset):
            png = UNSET
        else:
            png = PngExportFormatOption.from_dict(_png)

        _svg = d.pop("svg", UNSET)
        svg: SvgExportFormatOption | Unset
        if isinstance(_svg, Unset):
            svg = UNSET
        else:
            svg = SvgExportFormatOption.from_dict(_svg)

        _pptx = d.pop("pptx", UNSET)
        pptx: PptxExportFormatOption | Unset
        if isinstance(_pptx, Unset):
            pptx = UNSET
        else:
            pptx = PptxExportFormatOption.from_dict(_pptx)

        _gif = d.pop("gif", UNSET)
        gif: GifExportFormatOption | Unset
        if isinstance(_gif, Unset):
            gif = UNSET
        else:
            gif = GifExportFormatOption.from_dict(_gif)

        _mp4 = d.pop("mp4", UNSET)
        mp4: Mp4ExportFormatOption | Unset
        if isinstance(_mp4, Unset):
            mp4 = UNSET
        else:
            mp4 = Mp4ExportFormatOption.from_dict(_mp4)

        _html_bundle = d.pop("html_bundle", UNSET)
        html_bundle: HtmlBundleExportFormatOption | Unset
        if isinstance(_html_bundle, Unset):
            html_bundle = UNSET
        else:
            html_bundle = HtmlBundleExportFormatOption.from_dict(_html_bundle)

        _html_standalone = d.pop("html_standalone", UNSET)
        html_standalone: HtmlStandaloneExportFormatOption | Unset
        if isinstance(_html_standalone, Unset):
            html_standalone = UNSET
        else:
            html_standalone = HtmlStandaloneExportFormatOption.from_dict(_html_standalone)

        export_format_options = cls(
            pdf=pdf,
            jpg=jpg,
            png=png,
            svg=svg,
            pptx=pptx,
            gif=gif,
            mp4=mp4,
            html_bundle=html_bundle,
            html_standalone=html_standalone,
        )

        export_format_options.additional_properties = d
        return export_format_options

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
