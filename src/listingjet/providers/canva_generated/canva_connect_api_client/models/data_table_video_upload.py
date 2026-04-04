from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.data_table_ai_disclosure import DataTableAiDisclosure
from ..models.data_table_video_mime_type import DataTableVideoMimeType
from ..models.data_table_video_upload_type import DataTableVideoUploadType
from ..types import UNSET, Unset

T = TypeVar("T", bound="DataTableVideoUpload")


@_attrs_define
class DataTableVideoUpload:
    """Options for uploading a video asset.

    Attributes:
        type_ (DataTableVideoUploadType):
        url (str): The URL of the video file to upload.
        thumbnail_image_url (str): The URL of a thumbnail image to use as a fallback if thumbnailVideoUrl isn't
            provided.
            This can be an external URL or a data URL.
        mime_type (DataTableVideoMimeType): The MIME type of a video file that's supported by Canva's backend.
        ai_disclosure (DataTableAiDisclosure): A disclosure identifying if the app generated this media asset using AI.
        thumbnail_video_url (str | Unset): The URL of a thumbnail video to display while the video is queued for upload.
        width (int | Unset): The width of the video in pixels.
        height (int | Unset): The height of the video in pixels.
    """

    type_: DataTableVideoUploadType
    url: str
    thumbnail_image_url: str
    mime_type: DataTableVideoMimeType
    ai_disclosure: DataTableAiDisclosure
    thumbnail_video_url: str | Unset = UNSET
    width: int | Unset = UNSET
    height: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        url = self.url

        thumbnail_image_url = self.thumbnail_image_url

        mime_type = self.mime_type.value

        ai_disclosure = self.ai_disclosure.value

        thumbnail_video_url = self.thumbnail_video_url

        width = self.width

        height = self.height

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "url": url,
                "thumbnail_image_url": thumbnail_image_url,
                "mime_type": mime_type,
                "ai_disclosure": ai_disclosure,
            }
        )
        if thumbnail_video_url is not UNSET:
            field_dict["thumbnail_video_url"] = thumbnail_video_url
        if width is not UNSET:
            field_dict["width"] = width
        if height is not UNSET:
            field_dict["height"] = height

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = DataTableVideoUploadType(d.pop("type"))

        url = d.pop("url")

        thumbnail_image_url = d.pop("thumbnail_image_url")

        mime_type = DataTableVideoMimeType(d.pop("mime_type"))

        ai_disclosure = DataTableAiDisclosure(d.pop("ai_disclosure"))

        thumbnail_video_url = d.pop("thumbnail_video_url", UNSET)

        width = d.pop("width", UNSET)

        height = d.pop("height", UNSET)

        data_table_video_upload = cls(
            type_=type_,
            url=url,
            thumbnail_image_url=thumbnail_image_url,
            mime_type=mime_type,
            ai_disclosure=ai_disclosure,
            thumbnail_video_url=thumbnail_video_url,
            width=width,
            height=height,
        )

        data_table_video_upload.additional_properties = d
        return data_table_video_upload

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
