from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.dataset_filter import DatasetFilter
from ...models.error import Error
from ...models.list_brand_templates_response import ListBrandTemplatesResponse
from ...models.ownership_type import OwnershipType
from ...models.sort_by_type import SortByType
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 25,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    dataset: DatasetFilter | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["query"] = query

    params["continuation"] = continuation

    params["limit"] = limit

    json_ownership: str | Unset = UNSET
    if not isinstance(ownership, Unset):
        json_ownership = ownership.value

    params["ownership"] = json_ownership

    json_sort_by: str | Unset = UNSET
    if not isinstance(sort_by, Unset):
        json_sort_by = sort_by.value

    params["sort_by"] = json_sort_by

    json_dataset: str | Unset = UNSET
    if not isinstance(dataset, Unset):
        json_dataset = dataset.value

    params["dataset"] = json_dataset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/brand-templates",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | ListBrandTemplatesResponse:
    if response.status_code == 200:
        response_200 = ListBrandTemplatesResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | ListBrandTemplatesResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 25,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    dataset: DatasetFilter | Unset = UNSET,
) -> Response[Error | ListBrandTemplatesResponse]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get a list of the [brand templates](https://www.canva.com/help/publish-team-template/) the user has
    access to.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        limit (int | Unset):  Default: 25.
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        dataset (DatasetFilter | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListBrandTemplatesResponse]
    """

    kwargs = _get_kwargs(
        query=query,
        continuation=continuation,
        limit=limit,
        ownership=ownership,
        sort_by=sort_by,
        dataset=dataset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 25,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    dataset: DatasetFilter | Unset = UNSET,
) -> Error | ListBrandTemplatesResponse | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get a list of the [brand templates](https://www.canva.com/help/publish-team-template/) the user has
    access to.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        limit (int | Unset):  Default: 25.
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        dataset (DatasetFilter | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListBrandTemplatesResponse
    """

    return sync_detailed(
        client=client,
        query=query,
        continuation=continuation,
        limit=limit,
        ownership=ownership,
        sort_by=sort_by,
        dataset=dataset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 25,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    dataset: DatasetFilter | Unset = UNSET,
) -> Response[Error | ListBrandTemplatesResponse]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get a list of the [brand templates](https://www.canva.com/help/publish-team-template/) the user has
    access to.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        limit (int | Unset):  Default: 25.
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        dataset (DatasetFilter | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListBrandTemplatesResponse]
    """

    kwargs = _get_kwargs(
        query=query,
        continuation=continuation,
        limit=limit,
        ownership=ownership,
        sort_by=sort_by,
        dataset=dataset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    limit: int | Unset = 25,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    dataset: DatasetFilter | Unset = UNSET,
) -> Error | ListBrandTemplatesResponse | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get a list of the [brand templates](https://www.canva.com/help/publish-team-template/) the user has
    access to.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        limit (int | Unset):  Default: 25.
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        dataset (DatasetFilter | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListBrandTemplatesResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            query=query,
            continuation=continuation,
            limit=limit,
            ownership=ownership,
            sort_by=sort_by,
            dataset=dataset,
        )
    ).parsed
