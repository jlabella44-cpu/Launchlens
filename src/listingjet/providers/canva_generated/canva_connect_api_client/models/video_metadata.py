from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.video_metadata_type import VideoMetadataType
from ..types import UNSET, Unset

T = TypeVar("T", bound="VideoMetadata")


@_attrs_define
class VideoMetadata:
    """
    Attributes:
        type_ (VideoMetadataType):
        width (int): The width of the video in pixels. Example: 1920.
        height (int): The height of the video in pixels. Example: 1080.
        duration (int | Unset): The duration of the video in seconds. Example: 60.
    """

    type_: VideoMetadataType
    width: int
    height: int
    duration: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        width = self.width

        height = self.height

        duration = self.duration

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "width": width,
                "height": height,
            }
        )
        if duration is not UNSET:
            field_dict["duration"] = duration

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = VideoMetadataType(d.pop("type"))

        width = d.pop("width")

        height = d.pop("height")

        duration = d.pop("duration", UNSET)

        video_metadata = cls(
            type_=type_,
            width=width,
            height=height,
            duration=duration,
        )

        video_metadata.additional_properties = d
        return video_metadata

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
