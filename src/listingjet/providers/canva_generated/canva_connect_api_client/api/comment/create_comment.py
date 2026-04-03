from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_comment_request import CreateCommentRequest
from ...models.create_comment_response import CreateCommentResponse
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    *,
    body: CreateCommentRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/comments",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> CreateCommentResponse | Error:
    if response.status_code == 200:
        response_200 = CreateCommentResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

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
) -> Response[CreateCommentResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateCommentRequest,
) -> Response[CreateCommentResponse | Error]:
    """<Warning>

    This API is deprecated, so you should use the [Create
    thread](https://www.canva.dev/docs/connect/api-reference/comments/create-thread/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Create a new top-level comment on a design.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/). A design can have a maximum
    of 1000 comments.

    Args:
        body (CreateCommentRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateCommentResponse | Error]
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
    body: CreateCommentRequest,
) -> CreateCommentResponse | Error | None:
    """<Warning>

    This API is deprecated, so you should use the [Create
    thread](https://www.canva.dev/docs/connect/api-reference/comments/create-thread/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Create a new top-level comment on a design.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/). A design can have a maximum
    of 1000 comments.

    Args:
        body (CreateCommentRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateCommentResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateCommentRequest,
) -> Response[CreateCommentResponse | Error]:
    """<Warning>

    This API is deprecated, so you should use the [Create
    thread](https://www.canva.dev/docs/connect/api-reference/comments/create-thread/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Create a new top-level comment on a design.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/). A design can have a maximum
    of 1000 comments.

    Args:
        body (CreateCommentRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateCommentResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateCommentRequest,
) -> CreateCommentResponse | Error | None:
    """<Warning>

    This API is deprecated, so you should use the [Create
    thread](https://www.canva.dev/docs/connect/api-reference/comments/create-thread/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Create a new top-level comment on a design.
    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/). A design can have a maximum
    of 1000 comments.

    Args:
        body (CreateCommentRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateCommentResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
