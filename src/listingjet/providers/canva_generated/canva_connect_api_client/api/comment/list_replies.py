from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.list_replies_response import ListRepliesResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    design_id: str,
    thread_id: str,
    *,
    limit: int | Unset = 50,
    continuation: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["limit"] = limit

    params["continuation"] = continuation

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/designs/{design_id}/comments/{thread_id}/replies".format(
            design_id=quote(str(design_id), safe=""),
            thread_id=quote(str(thread_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListRepliesResponse:
    if response.status_code == 200:
        response_200 = ListRepliesResponse.from_dict(response.json())

        return response_200

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | ListRepliesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
    limit: int | Unset = 50,
    continuation: str | Unset = UNSET,
) -> Response[Error | ListRepliesResponse]:
    """<Warning>
    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.
    </Warning>

    Retrieves a list of replies for a comment or suggestion thread on a design.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        limit (int | Unset): The number of replies to return. Default: 50.
        continuation (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListRepliesResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        thread_id=thread_id,
        limit=limit,
        continuation=continuation,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
    limit: int | Unset = 50,
    continuation: str | Unset = UNSET,
) -> Error | ListRepliesResponse | None:
    """<Warning>
    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.
    </Warning>

    Retrieves a list of replies for a comment or suggestion thread on a design.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        limit (int | Unset): The number of replies to return. Default: 50.
        continuation (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListRepliesResponse
    """

    return sync_detailed(
        design_id=design_id,
        thread_id=thread_id,
        client=client,
        limit=limit,
        continuation=continuation,
    ).parsed


async def asyncio_detailed(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
    limit: int | Unset = 50,
    continuation: str | Unset = UNSET,
) -> Response[Error | ListRepliesResponse]:
    """<Warning>
    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.
    </Warning>

    Retrieves a list of replies for a comment or suggestion thread on a design.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        limit (int | Unset): The number of replies to return. Default: 50.
        continuation (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListRepliesResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        thread_id=thread_id,
        limit=limit,
        continuation=continuation,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
    limit: int | Unset = 50,
    continuation: str | Unset = UNSET,
) -> Error | ListRepliesResponse | None:
    """<Warning>
    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.
    </Warning>

    Retrieves a list of replies for a comment or suggestion thread on a design.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        limit (int | Unset): The number of replies to return. Default: 50.
        continuation (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListRepliesResponse
    """

    return (
        await asyncio_detailed(
            design_id=design_id,
            thread_id=thread_id,
            client=client,
            limit=limit,
            continuation=continuation,
        )
    ).parsed
