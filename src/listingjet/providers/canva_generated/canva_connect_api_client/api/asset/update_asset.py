from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.update_asset_request import UpdateAssetRequest
from ...models.update_asset_response import UpdateAssetResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    asset_id: str,
    *,
    body: UpdateAssetRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/assets/{asset_id}".format(
            asset_id=quote(str(asset_id), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | UpdateAssetResponse:
    if response.status_code == 200:
        response_200 = UpdateAssetResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | UpdateAssetResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    asset_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateAssetRequest | Unset = UNSET,
) -> Response[Error | UpdateAssetResponse]:
    """You can update the name and tags of an asset by specifying its `assetId`. Updating the tags
    replaces all existing tags of the asset.

    Args:
        asset_id (str):
        body (UpdateAssetRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | UpdateAssetResponse]
    """

    kwargs = _get_kwargs(
        asset_id=asset_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    asset_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateAssetRequest | Unset = UNSET,
) -> Error | UpdateAssetResponse | None:
    """You can update the name and tags of an asset by specifying its `assetId`. Updating the tags
    replaces all existing tags of the asset.

    Args:
        asset_id (str):
        body (UpdateAssetRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | UpdateAssetResponse
    """

    return sync_detailed(
        asset_id=asset_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    asset_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateAssetRequest | Unset = UNSET,
) -> Response[Error | UpdateAssetResponse]:
    """You can update the name and tags of an asset by specifying its `assetId`. Updating the tags
    replaces all existing tags of the asset.

    Args:
        asset_id (str):
        body (UpdateAssetRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | UpdateAssetResponse]
    """

    kwargs = _get_kwargs(
        asset_id=asset_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    asset_id: str,
    *,
    client: AuthenticatedClient,
    body: UpdateAssetRequest | Unset = UNSET,
) -> Error | UpdateAssetResponse | None:
    """You can update the name and tags of an asset by specifying its `assetId`. Updating the tags
    replaces all existing tags of the asset.

    Args:
        asset_id (str):
        body (UpdateAssetRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | UpdateAssetResponse
    """

    return (
        await asyncio_detailed(
            asset_id=asset_id,
            client=client,
            body=body,
        )
    ).parsed
