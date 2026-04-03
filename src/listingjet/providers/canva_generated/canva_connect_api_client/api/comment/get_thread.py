from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_thread_response import GetThreadResponse
from ...types import Response


def _get_kwargs(
    design_id: str,
    thread_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/designs/{design_id}/comments/{thread_id}".format(
            design_id=quote(str(design_id), safe=""),
            thread_id=quote(str(thread_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetThreadResponse:
    if response.status_code == 200:
        response_200 = GetThreadResponse.from_dict(response.json())

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
) -> Response[Error | GetThreadResponse]:
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
) -> Response[Error | GetThreadResponse]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Gets a comment or suggestion thread on a design.
    To retrieve a reply to a comment thread, use the [Get reply](https://www.canva.dev/docs/connect/api-
    reference/comments/get-reply/) API.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetThreadResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        thread_id=thread_id,
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
) -> Error | GetThreadResponse | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Gets a comment or suggestion thread on a design.
    To retrieve a reply to a comment thread, use the [Get reply](https://www.canva.dev/docs/connect/api-
    reference/comments/get-reply/) API.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetThreadResponse
    """

    return sync_detailed(
        design_id=design_id,
        thread_id=thread_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetThreadResponse]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Gets a comment or suggestion thread on a design.
    To retrieve a reply to a comment thread, use the [Get reply](https://www.canva.dev/docs/connect/api-
    reference/comments/get-reply/) API.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetThreadResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        thread_id=thread_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetThreadResponse | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Gets a comment or suggestion thread on a design.
    To retrieve a reply to a comment thread, use the [Get reply](https://www.canva.dev/docs/connect/api-
    reference/comments/get-reply/) API.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetThreadResponse
    """

    return (
        await asyncio_detailed(
            design_id=design_id,
            thread_id=thread_id,
            client=client,
        )
    ).parsed
