from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_folder_request import CreateFolderRequest
from ...models.create_folder_response import CreateFolderResponse
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    *,
    body: CreateFolderRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/folders",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> CreateFolderResponse | Error:
    if response.status_code == 200:
        response_200 = CreateFolderResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateFolderResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateFolderRequest,
) -> Response[CreateFolderResponse | Error]:
    """Creates a folder in one of the following locations:

    - The top level of a Canva user's [projects](https://www.canva.com/help/find-designs-and-folders/)
    (using the ID `root`),
    - The user's Uploads folder (using the ID `uploads`),
    - Another folder (using the parent folder's ID).

    When a folder is successfully created, the
    endpoint returns its folder ID, along with other information.

    Args:
        body (CreateFolderRequest): Body parameters for creating a new folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateFolderResponse | Error]
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
    body: CreateFolderRequest,
) -> CreateFolderResponse | Error | None:
    """Creates a folder in one of the following locations:

    - The top level of a Canva user's [projects](https://www.canva.com/help/find-designs-and-folders/)
    (using the ID `root`),
    - The user's Uploads folder (using the ID `uploads`),
    - Another folder (using the parent folder's ID).

    When a folder is successfully created, the
    endpoint returns its folder ID, along with other information.

    Args:
        body (CreateFolderRequest): Body parameters for creating a new folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateFolderResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateFolderRequest,
) -> Response[CreateFolderResponse | Error]:
    """Creates a folder in one of the following locations:

    - The top level of a Canva user's [projects](https://www.canva.com/help/find-designs-and-folders/)
    (using the ID `root`),
    - The user's Uploads folder (using the ID `uploads`),
    - Another folder (using the parent folder's ID).

    When a folder is successfully created, the
    endpoint returns its folder ID, along with other information.

    Args:
        body (CreateFolderRequest): Body parameters for creating a new folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateFolderResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateFolderRequest,
) -> CreateFolderResponse | Error | None:
    """Creates a folder in one of the following locations:

    - The top level of a Canva user's [projects](https://www.canva.com/help/find-designs-and-folders/)
    (using the ID `root`),
    - The user's Uploads folder (using the ID `uploads`),
    - Another folder (using the parent folder's ID).

    When a folder is successfully created, the
    endpoint returns its folder ID, along with other information.

    Args:
        body (CreateFolderRequest): Body parameters for creating a new folder.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateFolderResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
