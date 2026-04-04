from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DesignLinks")


@_attrs_define
class DesignLinks:
    """A temporary set of URLs for viewing or editing the design.

    Attributes:
        edit_url (str): A temporary editing URL for the design. This URL is only accessible to the user that made the
            API request, and is designed to support [return navigation](https://www.canva.dev/docs/connect/return-
            navigation-guide/) workflows.

            NOTE: This is not a permanent URL, it is only valid for 30 days. Example: https://www.canva.com/api/design/eyJhb
            GciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIiwiZXhwaXJ5IjoxNzQyMDk5NDAzMDc5fQ..GKLx2hrJa3wSSDKQ.hk3HA59qJyxehR-ejzt2DThBW0cb
            RdMBz7Fb5uCpwD-4o485pCf4kcXt_ypUYX0qMHVeZ131YvfwGPIhbk-C245D8c12IIJSDbZUZTS7WiCOJZQ.sNz3mPSQxsETBvl_-upMYA/edit.
        view_url (str): A temporary viewing URL for the design. This URL is only accessible to the user that made the
            API request, and is designed to support [return navigation](https://www.canva.dev/docs/connect/return-
            navigation-guide/) workflows.

            NOTE: This is not a permanent URL, it is only valid for 30 days.
             Example: https://www.canva.com/api/design/eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIiwiZXhwaXJ5IjoxNzQyMDk5NDAzMDc5f
            Q..GKLx2hrJa3wSSDKQ.hk3HA59qJyxehR-ejzt2DThBW0cbRdMBz7Fb5uCpwD-4o485pCf4kcXt_ypUYX0qMHVeZ131YvfwGPIhbk-
            C245D8c12IIJSDbZUZTS7WiCOJZQ.sNz3mPSQxsETBvl_-upMYA/view.
    """

    edit_url: str
    view_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        edit_url = self.edit_url

        view_url = self.view_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "edit_url": edit_url,
                "view_url": view_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        edit_url = d.pop("edit_url")

        view_url = d.pop("view_url")

        design_links = cls(
            edit_url=edit_url,
            view_url=view_url,
        )

        design_links.additional_properties = d
        return design_links

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
