from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.folder_item_pin_status import FolderItemPinStatus
from ...models.folder_item_sort_by import FolderItemSortBy
from ...models.folder_item_type import FolderItemType
from ...models.list_folder_items_response import ListFolderItemsResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    folder_id: str,
    *,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 50,
    item_types: list[FolderItemType] | Unset = UNSET,
    sort_by: FolderItemSortBy | Unset = UNSET,
    pin_status: FolderItemPinStatus | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["continuation"] = continuation

    params["limit"] = limit

    json_item_types: list[str] | Unset = UNSET
    if not isinstance(item_types, Unset):
        json_item_types = []
        for item_types_item_data in item_types:
            item_types_item = item_types_item_data.value
            json_item_types.append(item_types_item)

    params["item_types"] = json_item_types

    json_sort_by: str | Unset = UNSET
    if not isinstance(sort_by, Unset):
        json_sort_by = sort_by.value

    params["sort_by"] = json_sort_by

    json_pin_status: str | Unset = UNSET
    if not isinstance(pin_status, Unset):
        json_pin_status = pin_status.value

    params["pin_status"] = json_pin_status

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/folders/{folder_id}/items".format(
            folder_id=quote(str(folder_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | ListFolderItemsResponse:
    if response.status_code == 200:
        response_200 = ListFolderItemsResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | ListFolderItemsResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 50,
    item_types: list[FolderItemType] | Unset = UNSET,
    sort_by: FolderItemSortBy | Unset = UNSET,
    pin_status: FolderItemPinStatus | Unset = UNSET,
) -> Response[Error | ListFolderItemsResponse]:
    """Lists the items in a folder, including each item's `type`.

    Folders can contain:

    - Other folders.
    - Designs, such as Instagram posts, Presentations, and Documents ([Canva
    Docs](https://www.canva.com/create/documents/)).
    - Image assets.

    Currently, video assets are not returned in the response.

    Args:
        folder_id (str):
        continuation (str | Unset):
        limit (int | Unset): The number of folder items to return. Default: 50.
        item_types (list[FolderItemType] | Unset):
        sort_by (FolderItemSortBy | Unset):
        pin_status (FolderItemPinStatus | Unset): Filter folder items by their pinned status.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListFolderItemsResponse]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
        continuation=continuation,
        limit=limit,
        item_types=item_types,
        sort_by=sort_by,
        pin_status=pin_status,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 50,
    item_types: list[FolderItemType] | Unset = UNSET,
    sort_by: FolderItemSortBy | Unset = UNSET,
    pin_status: FolderItemPinStatus | Unset = UNSET,
) -> Error | ListFolderItemsResponse | None:
    """Lists the items in a folder, including each item's `type`.

    Folders can contain:

    - Other folders.
    - Designs, such as Instagram posts, Presentations, and Documents ([Canva
    Docs](https://www.canva.com/create/documents/)).
    - Image assets.

    Currently, video assets are not returned in the response.

    Args:
        folder_id (str):
        continuation (str | Unset):
        limit (int | Unset): The number of folder items to return. Default: 50.
        item_types (list[FolderItemType] | Unset):
        sort_by (FolderItemSortBy | Unset):
        pin_status (FolderItemPinStatus | Unset): Filter folder items by their pinned status.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListFolderItemsResponse
    """

    return sync_detailed(
        folder_id=folder_id,
        client=client,
        continuation=continuation,
        limit=limit,
        item_types=item_types,
        sort_by=sort_by,
        pin_status=pin_status,
    ).parsed


async def asyncio_detailed(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 50,
    item_types: list[FolderItemType] | Unset = UNSET,
    sort_by: FolderItemSortBy | Unset = UNSET,
    pin_status: FolderItemPinStatus | Unset = UNSET,
) -> Response[Error | ListFolderItemsResponse]:
    """Lists the items in a folder, including each item's `type`.

    Folders can contain:

    - Other folders.
    - Designs, such as Instagram posts, Presentations, and Documents ([Canva
    Docs](https://www.canva.com/create/documents/)).
    - Image assets.

    Currently, video assets are not returned in the response.

    Args:
        folder_id (str):
        continuation (str | Unset):
        limit (int | Unset): The number of folder items to return. Default: 50.
        item_types (list[FolderItemType] | Unset):
        sort_by (FolderItemSortBy | Unset):
        pin_status (FolderItemPinStatus | Unset): Filter folder items by their pinned status.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListFolderItemsResponse]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
        continuation=continuation,
        limit=limit,
        item_types=item_types,
        sort_by=sort_by,
        pin_status=pin_status,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 50,
    item_types: list[FolderItemType] | Unset = UNSET,
    sort_by: FolderItemSortBy | Unset = UNSET,
    pin_status: FolderItemPinStatus | Unset = UNSET,
) -> Error | ListFolderItemsResponse | None:
    """Lists the items in a folder, including each item's `type`.

    Folders can contain:

    - Other folders.
    - Designs, such as Instagram posts, Presentations, and Documents ([Canva
    Docs](https://www.canva.com/create/documents/)).
    - Image assets.

    Currently, video assets are not returned in the response.

    Args:
        folder_id (str):
        continuation (str | Unset):
        limit (int | Unset): The number of folder items to return. Default: 50.
        item_types (list[FolderItemType] | Unset):
        sort_by (FolderItemSortBy | Unset):
        pin_status (FolderItemPinStatus | Unset): Filter folder items by their pinned status.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListFolderItemsResponse
    """

    return (
        await asyncio_detailed(
            folder_id=folder_id,
            client=client,
            continuation=continuation,
            limit=limit,
            item_types=item_types,
            sort_by=sort_by,
            pin_status=pin_status,
        )
    ).parsed
