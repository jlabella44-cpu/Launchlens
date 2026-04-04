from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_design_pages_response import GetDesignPagesResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    design_id: str,
    *,
    offset: int | Unset = 1,
    limit: int | Unset = 50,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["offset"] = offset

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/designs/{design_id}/pages".format(
            design_id=quote(str(design_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetDesignPagesResponse:
    if response.status_code == 200:
        response_200 = GetDesignPagesResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetDesignPagesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    design_id: str,
    *,
    client: AuthenticatedClient,
    offset: int | Unset = 1,
    limit: int | Unset = 50,
) -> Response[Error | GetDesignPagesResponse]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Lists metadata for pages in a design, such as page-specific thumbnails.

    For the specified design, you can provide `offset` and `limit` values to specify the range of pages
    to return.

    NOTE: Some design types don't have pages (for example, Canva docs).

    Args:
        design_id (str):
        offset (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignPagesResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        offset=offset,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    design_id: str,
    *,
    client: AuthenticatedClient,
    offset: int | Unset = 1,
    limit: int | Unset = 50,
) -> Error | GetDesignPagesResponse | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Lists metadata for pages in a design, such as page-specific thumbnails.

    For the specified design, you can provide `offset` and `limit` values to specify the range of pages
    to return.

    NOTE: Some design types don't have pages (for example, Canva docs).

    Args:
        design_id (str):
        offset (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignPagesResponse
    """

    return sync_detailed(
        design_id=design_id,
        client=client,
        offset=offset,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    design_id: str,
    *,
    client: AuthenticatedClient,
    offset: int | Unset = 1,
    limit: int | Unset = 50,
) -> Response[Error | GetDesignPagesResponse]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Lists metadata for pages in a design, such as page-specific thumbnails.

    For the specified design, you can provide `offset` and `limit` values to specify the range of pages
    to return.

    NOTE: Some design types don't have pages (for example, Canva docs).

    Args:
        design_id (str):
        offset (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignPagesResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
        offset=offset,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    design_id: str,
    *,
    client: AuthenticatedClient,
    offset: int | Unset = 1,
    limit: int | Unset = 50,
) -> Error | GetDesignPagesResponse | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Lists metadata for pages in a design, such as page-specific thumbnails.

    For the specified design, you can provide `offset` and `limit` values to specify the range of pages
    to return.

    NOTE: Some design types don't have pages (for example, Canva docs).

    Args:
        design_id (str):
        offset (int | Unset):  Default: 1.
        limit (int | Unset):  Default: 50.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignPagesResponse
    """

    return (
        await asyncio_detailed(
            design_id=design_id,
            client=client,
            offset=offset,
            limit=limit,
        )
    ).parsed
