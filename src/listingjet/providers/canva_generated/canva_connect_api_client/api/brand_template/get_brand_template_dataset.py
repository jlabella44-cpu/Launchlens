from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_brand_template_dataset_response import GetBrandTemplateDatasetResponse
from ...types import Response


def _get_kwargs(
    brand_template_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/brand-templates/{brand_template_id}/dataset".format(
            brand_template_id=quote(str(brand_template_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetBrandTemplateDatasetResponse:
    if response.status_code == 200:
        response_200 = GetBrandTemplateDatasetResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetBrandTemplateDatasetResponse]:
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
) -> Response[Error | GetBrandTemplateDatasetResponse]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Gets the dataset definition of a brand template. If the brand
    template contains autofill data fields, this API returns an object with the data field
    names and the type of data they accept.

    Available data field types include:

    - Images
    - Text
    - Charts

    You can autofill a brand template using the [Create a design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetBrandTemplateDatasetResponse]
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
) -> Error | GetBrandTemplateDatasetResponse | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Gets the dataset definition of a brand template. If the brand
    template contains autofill data fields, this API returns an object with the data field
    names and the type of data they accept.

    Available data field types include:

    - Images
    - Text
    - Charts

    You can autofill a brand template using the [Create a design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetBrandTemplateDatasetResponse
    """

    return sync_detailed(
        brand_template_id=brand_template_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    brand_template_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetBrandTemplateDatasetResponse]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Gets the dataset definition of a brand template. If the brand
    template contains autofill data fields, this API returns an object with the data field
    names and the type of data they accept.

    Available data field types include:

    - Images
    - Text
    - Charts

    You can autofill a brand template using the [Create a design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetBrandTemplateDatasetResponse]
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
) -> Error | GetBrandTemplateDatasetResponse | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Gets the dataset definition of a brand template. If the brand
    template contains autofill data fields, this API returns an object with the data field
    names and the type of data they accept.

    Available data field types include:

    - Images
    - Text
    - Charts

    You can autofill a brand template using the [Create a design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    Args:
        brand_template_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetBrandTemplateDatasetResponse
    """

    return (
        await asyncio_detailed(
            brand_template_id=brand_template_id,
            client=client,
        )
    ).parsed
