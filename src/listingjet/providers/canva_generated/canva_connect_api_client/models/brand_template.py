from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.thumbnail import Thumbnail


T = TypeVar("T", bound="BrandTemplate")


@_attrs_define
class BrandTemplate:
    """An object representing a brand template with associated metadata.

    Attributes:
        id (str): The brand template ID. Example: DEMzWSwy3BI.
        title (str): The brand template title, as shown in the Canva UI. Example: Advertisement Template.
        view_url (str): A URL Canva users can visit to view the brand template. Example:
            https://www.canva.com/design/DAE35hE8FA4/view.
        create_url (str): A URL Canva users can visit to create a new design from the template. Example:
            https://www.canva.com/design/DAE35hE8FA4/remix.
        created_at (int): When the brand template was created, as a Unix timestamp
            (in seconds since the Unix Epoch). Example: 1704110400.
        updated_at (int): When the brand template was last updated, as a Unix timestamp
            (in seconds since the Unix Epoch). Example: 1719835200.
        thumbnail (Thumbnail | Unset): A thumbnail image representing the object.
    """

    id: str
    title: str
    view_url: str
    create_url: str
    created_at: int
    updated_at: int
    thumbnail: Thumbnail | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        title = self.title

        view_url = self.view_url

        create_url = self.create_url

        created_at = self.created_at

        updated_at = self.updated_at

        thumbnail: dict[str, Any] | Unset = UNSET
        if not isinstance(self.thumbnail, Unset):
            thumbnail = self.thumbnail.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "title": title,
                "view_url": view_url,
                "create_url": create_url,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if thumbnail is not UNSET:
            field_dict["thumbnail"] = thumbnail

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.thumbnail import Thumbnail

        d = dict(src_dict)
        id = d.pop("id")

        title = d.pop("title")

        view_url = d.pop("view_url")

        create_url = d.pop("create_url")

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        _thumbnail = d.pop("thumbnail", UNSET)
        thumbnail: Thumbnail | Unset
        if isinstance(_thumbnail, Unset):
            thumbnail = UNSET
        else:
            thumbnail = Thumbnail.from_dict(_thumbnail)

        brand_template = cls(
            id=id,
            title=title,
            view_url=view_url,
            create_url=create_url,
            created_at=created_at,
            updated_at=updated_at,
            thumbnail=thumbnail,
        )

        brand_template.additional_properties = d
        return brand_template

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
