from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_app_jwks_response import GetAppJwksResponse
from ...types import Response


def _get_kwargs(
    app_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/apps/{app_id}/jwks".format(
            app_id=quote(str(app_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetAppJwksResponse:
    if response.status_code == 200:
        response_200 = GetAppJwksResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetAppJwksResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    app_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | GetAppJwksResponse]:
    """Returns the Json Web Key Set (public keys) of an app. These keys are used to
    verify JWTs sent to app backends.

    Args:
        app_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetAppJwksResponse]
    """

    kwargs = _get_kwargs(
        app_id=app_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    app_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Error | GetAppJwksResponse | None:
    """Returns the Json Web Key Set (public keys) of an app. These keys are used to
    verify JWTs sent to app backends.

    Args:
        app_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetAppJwksResponse
    """

    return sync_detailed(
        app_id=app_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    app_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | GetAppJwksResponse]:
    """Returns the Json Web Key Set (public keys) of an app. These keys are used to
    verify JWTs sent to app backends.

    Args:
        app_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetAppJwksResponse]
    """

    kwargs = _get_kwargs(
        app_id=app_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    app_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Error | GetAppJwksResponse | None:
    """Returns the Json Web Key Set (public keys) of an app. These keys are used to
    verify JWTs sent to app backends.

    Args:
        app_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetAppJwksResponse
    """

    return (
        await asyncio_detailed(
            app_id=app_id,
            client=client,
        )
    ).parsed
