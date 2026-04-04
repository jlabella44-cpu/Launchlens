from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.design_links import DesignLinks
    from ..models.team_user_summary import TeamUserSummary
    from ..models.thumbnail import Thumbnail


T = TypeVar("T", bound="Design")


@_attrs_define
class Design:
    """The design object, which contains metadata about the design.

    Attributes:
        id (str): The design ID. Example: DAFVztcvd9z.
        owner (TeamUserSummary): Metadata for the user, consisting of the User ID and Team ID.
        urls (DesignLinks): A temporary set of URLs for viewing or editing the design.
        created_at (int): When the design was created in Canva, as a Unix timestamp (in seconds since the Unix
            Epoch). Example: 1377396000.
        updated_at (int): When the design was last updated in Canva, as a Unix timestamp (in seconds since the
            Unix Epoch). Example: 1692928800.
        title (str | Unset): The design title. Example: My summer holiday.
        thumbnail (Thumbnail | Unset): A thumbnail image representing the object.
        page_count (int | Unset): The total number of pages in the design. Some design types don't have pages (for
            example, Canva docs). Example: 5.
    """

    id: str
    owner: TeamUserSummary
    urls: DesignLinks
    created_at: int
    updated_at: int
    title: str | Unset = UNSET
    thumbnail: Thumbnail | Unset = UNSET
    page_count: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        owner = self.owner.to_dict()

        urls = self.urls.to_dict()

        created_at = self.created_at

        updated_at = self.updated_at

        title = self.title

        thumbnail: dict[str, Any] | Unset = UNSET
        if not isinstance(self.thumbnail, Unset):
            thumbnail = self.thumbnail.to_dict()

        page_count = self.page_count

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "owner": owner,
                "urls": urls,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if thumbnail is not UNSET:
            field_dict["thumbnail"] = thumbnail
        if page_count is not UNSET:
            field_dict["page_count"] = page_count

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.design_links import DesignLinks
        from ..models.team_user_summary import TeamUserSummary
        from ..models.thumbnail import Thumbnail

        d = dict(src_dict)
        id = d.pop("id")

        owner = TeamUserSummary.from_dict(d.pop("owner"))

        urls = DesignLinks.from_dict(d.pop("urls"))

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        title = d.pop("title", UNSET)

        _thumbnail = d.pop("thumbnail", UNSET)
        thumbnail: Thumbnail | Unset
        if isinstance(_thumbnail, Unset):
            thumbnail = UNSET
        else:
            thumbnail = Thumbnail.from_dict(_thumbnail)

        page_count = d.pop("page_count", UNSET)

        design = cls(
            id=id,
            owner=owner,
            urls=urls,
            created_at=created_at,
            updated_at=updated_at,
            title=title,
            thumbnail=thumbnail,
            page_count=page_count,
        )

        design.additional_properties = d
        return design

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
