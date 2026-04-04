from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_reply_v2_request import CreateReplyV2Request
from ...models.create_reply_v2_response import CreateReplyV2Response
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    design_id: str,
    thread_id: str,
    *,
    body: CreateReplyV2Request,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/designs/{design_id}/comments/{thread_id}/replies".format(
            design_id=quote(str(design_id), safe=""),
            thread_id=quote(str(thread_id), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> CreateReplyV2Response | Error:
    if response.status_code == 200:
        response_200 = CreateReplyV2Response.from_dict(response.json())

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
) -> Response[CreateReplyV2Response | Error]:
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
    body: CreateReplyV2Request,
) -> Response[CreateReplyV2Response | Error]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment or suggestion thread on a design.
    To reply to an existing thread, you must provide the ID of the thread
    which is returned when a thread is created, or from the `thread_id` value
    of an existing reply in the thread. Each thread can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        body (CreateReplyV2Request):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateReplyV2Response | Error]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        thread_id=thread_id,
        body=body,
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
    body: CreateReplyV2Request,
) -> CreateReplyV2Response | Error | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment or suggestion thread on a design.
    To reply to an existing thread, you must provide the ID of the thread
    which is returned when a thread is created, or from the `thread_id` value
    of an existing reply in the thread. Each thread can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        body (CreateReplyV2Request):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateReplyV2Response | Error
    """

    return sync_detailed(
        design_id=design_id,
        thread_id=thread_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
    body: CreateReplyV2Request,
) -> Response[CreateReplyV2Response | Error]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment or suggestion thread on a design.
    To reply to an existing thread, you must provide the ID of the thread
    which is returned when a thread is created, or from the `thread_id` value
    of an existing reply in the thread. Each thread can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        body (CreateReplyV2Request):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateReplyV2Response | Error]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        thread_id=thread_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    design_id: str,
    thread_id: str,
    *,
    client: AuthenticatedClient,
    body: CreateReplyV2Request,
) -> CreateReplyV2Response | Error | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Creates a reply to a comment or suggestion thread on a design.
    To reply to an existing thread, you must provide the ID of the thread
    which is returned when a thread is created, or from the `thread_id` value
    of an existing reply in the thread. Each thread can
    have a maximum of 100 replies created for it.

    For information on comments and how they're used in the Canva UI, see the
    [Canva Help Center](https://www.canva.com/help/comments/).

    Args:
        design_id (str):
        thread_id (str):
        body (CreateReplyV2Request):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateReplyV2Response | Error
    """

    return (
        await asyncio_detailed(
            design_id=design_id,
            thread_id=thread_id,
            client=client,
            body=body,
        )
    ).parsed
