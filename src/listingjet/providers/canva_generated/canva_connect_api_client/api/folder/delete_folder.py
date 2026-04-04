from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    folder_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/v1/folders/{folder_id}".format(
            folder_id=quote(str(folder_id), safe=""),
        ),
    }

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
    folder_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Any | Error]:
    """Deletes a folder with the specified `folderID`.
    Deleting a folder moves the user's content in the folder to the
    [Trash](https://www.canva.com/help/deleted-designs/) and content owned by
    other users is moved to the top level of the owner's
    [projects](https://www.canva.com/help/find-designs-and-folders/).

    Args:
        folder_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    folder_id: str,
    *,
    client: AuthenticatedClient,
) -> Any | Error | None:
    """Deletes a folder with the specified `folderID`.
    Deleting a folder moves the user's content in the folder to the
    [Trash](https://www.canva.com/help/deleted-designs/) and content owned by
    other users is moved to the top level of the owner's
    [projects](https://www.canva.com/help/find-designs-and-folders/).

    Args:
        folder_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error
    """

    return sync_detailed(
        folder_id=folder_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    folder_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Any | Error]:
    """Deletes a folder with the specified `folderID`.
    Deleting a folder moves the user's content in the folder to the
    [Trash](https://www.canva.com/help/deleted-designs/) and content owned by
    other users is moved to the top level of the owner's
    [projects](https://www.canva.com/help/find-designs-and-folders/).

    Args:
        folder_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | Error]
    """

    kwargs = _get_kwargs(
        folder_id=folder_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    folder_id: str,
    *,
    client: AuthenticatedClient,
) -> Any | Error | None:
    """Deletes a folder with the specified `folderID`.
    Deleting a folder moves the user's content in the folder to the
    [Trash](https://www.canva.com/help/deleted-designs/) and content owned by
    other users is moved to the top level of the owner's
    [projects](https://www.canva.com/help/find-designs-and-folders/).

    Args:
        folder_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | Error
    """

    return (
        await asyncio_detailed(
            folder_id=folder_id,
            client=client,
        )
    ).parsed
