from http import HTTPStatus
from typing import Any, cast

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.move_folder_item_request import MoveFolderItemRequest
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: MoveFolderItemRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/folders/move",
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | Error:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: MoveFolderItemRequest | Unset = UNSET,
) -> Response[Any | Error]:
    """Moves an item to another folder. You must specify the folder ID of the destination folder, as well
    as the ID of the item you want to move.

    NOTE: In some situations, a single item can exist in multiple folders. If you attempt to move an
    item that exists in multiple folders, the API returns an `item_in_multiple_folders` error. In this
    case, you must use the Canva UI to move the item to another folder.

    Args:
        body (MoveFolderItemRequest | Unset): Body parameters for moving the folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: MoveFolderItemRequest | Unset = UNSET,
) -> Any | Error | None:
    """Moves an item to another folder. You must specify the folder ID of the destination folder, as well
    as the ID of the item you want to move.

    NOTE: In some situations, a single item can exist in multiple folders. If you attempt to move an
    item that exists in multiple folders, the API returns an `item_in_multiple_folders` error. In this
    case, you must use the Canva UI to move the item to another folder.

    Args:
        body (MoveFolderItemRequest | Unset): Body parameters for moving the folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: MoveFolderItemRequest | Unset = UNSET,
) -> Response[Any | Error]:
    """Moves an item to another folder. You must specify the folder ID of the destination folder, as well
    as the ID of the item you want to move.

    NOTE: In some situations, a single item can exist in multiple folders. If you attempt to move an
    item that exists in multiple folders, the API returns an `item_in_multiple_folders` error. In this
    case, you must use the Canva UI to move the item to another folder.

    Args:
        body (MoveFolderItemRequest | Unset): Body parameters for moving the folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: MoveFolderItemRequest | Unset = UNSET,
) -> Any | Error | None:
    """Moves an item to another folder. You must specify the folder ID of the destination folder, as well
    as the ID of the item you want to move.

    NOTE: In some situations, a single item can exist in multiple folders. If you attempt to move an
    item that exists in multiple folders, the API returns an `item_in_multiple_folders` error. In this
    case, you must use the Canva UI to move the item to another folder.

    Args:
        body (MoveFolderItemRequest | Unset): Body parameters for moving the folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
