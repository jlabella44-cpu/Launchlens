from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_reply_request import CreateReplyRequest
from ...models.create_reply_response import CreateReplyResponse
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    comment_id: str,
    *,
    body: CreateReplyRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/comments/{comment_id}/replies".format(
            comment_id=quote(str(comment_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> CreateReplyResponse | Error:
    if response.status_code == 200:
        response_200 = CreateReplyResponse.from_dict(response.json())

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
) -> Response[CreateReplyResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    comment_id: str,
    *,
    client: AuthenticatedClient,
    body: CreateReplyRequest,
) -> Response[CreateReplyResponse | Error]:
    """<Warning>

    This API is deprecated, so you should use the [Create reply](https://www.canva.dev/docs/connect/api-
    reference/comments/create-reply/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment in a design.
    To reply to an existing thread of comments, you can use either the `id` of the parent
    (original) comment, or the `thread_id` of a comment in the thread. Each comment can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        comment_id (str):
        body (CreateReplyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateReplyResponse | Error]
    """

    kwargs = _get_kwargs(
        comment_id=comment_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    comment_id: str,
    *,
    client: AuthenticatedClient,
    body: CreateReplyRequest,
) -> CreateReplyResponse | Error | None:
    """<Warning>

    This API is deprecated, so you should use the [Create reply](https://www.canva.dev/docs/connect/api-
    reference/comments/create-reply/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment in a design.
    To reply to an existing thread of comments, you can use either the `id` of the parent
    (original) comment, or the `thread_id` of a comment in the thread. Each comment can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        comment_id (str):
        body (CreateReplyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateReplyResponse | Error
    """

    return sync_detailed(
        comment_id=comment_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    comment_id: str,
    *,
    client: AuthenticatedClient,
    body: CreateReplyRequest,
) -> Response[CreateReplyResponse | Error]:
    """<Warning>

    This API is deprecated, so you should use the [Create reply](https://www.canva.dev/docs/connect/api-
    reference/comments/create-reply/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment in a design.
    To reply to an existing thread of comments, you can use either the `id` of the parent
    (original) comment, or the `thread_id` of a comment in the thread. Each comment can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        comment_id (str):
        body (CreateReplyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateReplyResponse | Error]
    """

    kwargs = _get_kwargs(
        comment_id=comment_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    comment_id: str,
    *,
    client: AuthenticatedClient,
    body: CreateReplyRequest,
) -> CreateReplyResponse | Error | None:
    """<Warning>

    This API is deprecated, so you should use the [Create reply](https://www.canva.dev/docs/connect/api-
    reference/comments/create-reply/) API instead.

    </Warning>

    <Warning>

    This API is currently provided as a preview. Be aware of the following:
    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment in a design.
    To reply to an existing thread of comments, you can use either the `id` of the parent
    (original) comment, or the `thread_id` of a comment in the thread. Each comment can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        comment_id (str):
        body (CreateReplyRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateReplyResponse | Error
    """

    return (
        await asyncio_detailed(
            comment_id=comment_id,
            client=client,
            body=body,
        )
    ).parsed
