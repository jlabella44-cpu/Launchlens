from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.update_folder_request import UpdateFolderRequest
from ...models.update_folder_response import UpdateFolderResponse
from ...types import Response


def _get_kwargs(
    folder_id: str,
    *,
    body: UpdateFolderRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/folders/{folder_id}".format(
            folder_id=quote(str(folder_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | UpdateFolderResponse:
    if response.status_code == 200:
        response_200 = UpdateFolderResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | UpdateFolderResponse]:
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
    body: UpdateFolderRequest,
) -> Response[Error | UpdateFolderResponse]:
    """Updates a folder's details using its `folderID`.
    Currently, you can only update a folder's name.

    Args:
        folder_id (str):
        body (UpdateFolderRequest): Body parameters for updating the folder's details.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | UpdateFolderResponse]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateFolderRequest,
) -> Error | UpdateFolderResponse | None:
    """Updates a folder's details using its `folderID`.
    Currently, you can only update a folder's name.

    Args:
        folder_id (str):
        body (UpdateFolderRequest): Body parameters for updating the folder's details.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | UpdateFolderResponse
    """

    return sync_detailed(
        folder_id=folder_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateFolderRequest,
) -> Response[Error | UpdateFolderResponse]:
    """Updates a folder's details using its `folderID`.
    Currently, you can only update a folder's name.

    Args:
        folder_id (str):
        body (UpdateFolderRequest): Body parameters for updating the folder's details.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | UpdateFolderResponse]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    folder_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateFolderRequest,
) -> Error | UpdateFolderResponse | None:
    """Updates a folder's details using its `folderID`.
    Currently, you can only update a folder's name.

    Args:
        folder_id (str):
        body (UpdateFolderRequest): Body parameters for updating the folder's details.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | UpdateFolderResponse
    """

    return (
        await asyncio_detailed(
            folder_id=folder_id,
            client=client,
            body=body,
        )
    ).parsed
