from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.data_table_ai_disclosure import DataTableAiDisclosure
from ..models.data_table_image_mime_type import DataTableImageMimeType
from ..models.data_table_image_upload_type import DataTableImageUploadType
from ..types import UNSET, Unset

T = TypeVar("T", bound="DataTableImageUpload")


@_attrs_define
class DataTableImageUpload:
    """Options for uploading an image asset.

    Attributes:
        type_ (DataTableImageUploadType):
        url (str): The URL of the image file to upload.
            This can be an external URL or a data URL.
        thumbnail_url (str): The URL of a thumbnail image to display while the image is queued for upload.
            This can be an external URL or a data URL.
        mime_type (DataTableImageMimeType): The MIME type of an image file that's supported by Canva's backend.
        ai_disclosure (DataTableAiDisclosure): A disclosure identifying if the app generated this media asset using AI.
        width (int | Unset): The width of the image in pixels.
        height (int | Unset): The height of the image in pixels.
    """

    type_: DataTableImageUploadType
    url: str
    thumbnail_url: str
    mime_type: DataTableImageMimeType
    ai_disclosure: DataTableAiDisclosure
    width: int | Unset = UNSET
    height: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        url = self.url

        thumbnail_url = self.thumbnail_url

        mime_type = self.mime_type.value

        ai_disclosure = self.ai_disclosure.value

        width = self.width

        height = self.height

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "url": url,
                "thumbnail_url": thumbnail_url,
                "mime_type": mime_type,
                "ai_disclosure": ai_disclosure,
            }
        )
        if width is not UNSET:
            field_dict["width"] = width
        if height is not UNSET:
            field_dict["height"] = height

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = DataTableImageUploadType(d.pop("type"))

        url = d.pop("url")

        thumbnail_url = d.pop("thumbnail_url")

        mime_type = DataTableImageMimeType(d.pop("mime_type"))

        ai_disclosure = DataTableAiDisclosure(d.pop("ai_disclosure"))

        width = d.pop("width", UNSET)

        height = d.pop("height", UNSET)

        data_table_image_upload = cls(
            type_=type_,
            url=url,
            thumbnail_url=thumbnail_url,
            mime_type=mime_type,
            ai_disclosure=ai_disclosure,
            width=width,
            height=height,
        )

        data_table_image_upload.additional_properties = d
        return data_table_image_upload

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
