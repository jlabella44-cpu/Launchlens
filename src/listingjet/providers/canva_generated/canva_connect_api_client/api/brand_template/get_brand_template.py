from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_brand_template_response import GetBrandTemplateResponse
from ...types import Response


def _get_kwargs(
    brand_template_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/brand-templates/{brand_template_id}".format(
            brand_template_id=quote(str(brand_template_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetBrandTemplateResponse:
    if response.status_code == 200:
        response_200 = GetBrandTemplateResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetBrandTemplateResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    brand_template_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetBrandTemplateResponse]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Retrieves the metadata for a brand template.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetBrandTemplateResponse]
    """

    kwargs = _get_kwargs(
        brand_template_id=brand_template_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    brand_template_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetBrandTemplateResponse | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Retrieves the metadata for a brand template.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetBrandTemplateResponse
    """

    return sync_detailed(
        brand_template_id=brand_template_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    brand_template_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetBrandTemplateResponse]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Retrieves the metadata for a brand template.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetBrandTemplateResponse]
    """

    kwargs = _get_kwargs(
        brand_template_id=brand_template_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    brand_template_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetBrandTemplateResponse | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Retrieves the metadata for a brand template.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetBrandTemplateResponse
    """

    return (
        await asyncio_detailed(
            brand_template_id=brand_template_id,
            client=client,
        )
    ).parsed
