from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_design_response import GetDesignResponse
from ...types import Response


def _get_kwargs(
    design_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/designs/{design_id}".format(
            design_id=quote(str(design_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetDesignResponse:
    if response.status_code == 200:
        response_200 = GetDesignResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetDesignResponse]:
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
) -> Response[Error | GetDesignResponse]:
    """Gets the metadata for a design. This includes owner information, URLs for editing and viewing, and
    thumbnail information.

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    design_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetDesignResponse | None:
    """Gets the metadata for a design. This includes owner information, URLs for editing and viewing, and
    thumbnail information.

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignResponse
    """

    return sync_detailed(
        design_id=design_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    design_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignResponse]:
    """Gets the metadata for a design. This includes owner information, URLs for editing and viewing, and
    thumbnail information.

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignResponse]
    """

    kwargs = _get_kwargs(
        design_id=design_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    design_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetDesignResponse | None:
    """Gets the metadata for a design. This includes owner information, URLs for editing and viewing, and
    thumbnail information.

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignResponse
    """

    return (
        await asyncio_detailed(
            design_id=design_id,
            client=client,
        )
    ).parsed
