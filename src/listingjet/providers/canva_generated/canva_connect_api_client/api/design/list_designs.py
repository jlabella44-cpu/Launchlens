from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_list_design_response import GetListDesignResponse
from ...models.ownership_type import OwnershipType
from ...models.sort_by_type import SortByType
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    limit: int | Unset = 25,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["query"] = query

    params["continuation"] = continuation

    json_ownership: str | Unset = UNSET
    if not isinstance(ownership, Unset):
        json_ownership = ownership.value

    params["ownership"] = json_ownership

    json_sort_by: str | Unset = UNSET
    if not isinstance(sort_by, Unset):
        json_sort_by = sort_by.value

    params["sort_by"] = json_sort_by

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/designs",
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetListDesignResponse:
    if response.status_code == 200:
        response_200 = GetListDesignResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetListDesignResponse]:
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
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    limit: int | Unset = 25,
) -> Response[Error | GetListDesignResponse]:
    """Lists metadata for all the designs in a Canva user's
    [projects](https://www.canva.com/help/find-designs-and-folders/). You can also:

    - Use search terms to filter the listed designs.
    - Show designs either created by, or shared with the user.
    - Sort the results.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetListDesignResponse]
    """

    kwargs = _get_kwargs(
        query=query,
        continuation=continuation,
        ownership=ownership,
        sort_by=sort_by,
        limit=limit,
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
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    limit: int | Unset = 25,
) -> Error | GetListDesignResponse | None:
    """Lists metadata for all the designs in a Canva user's
    [projects](https://www.canva.com/help/find-designs-and-folders/). You can also:

    - Use search terms to filter the listed designs.
    - Show designs either created by, or shared with the user.
    - Sort the results.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetListDesignResponse
    """

    return sync_detailed(
        client=client,
        query=query,
        continuation=continuation,
        ownership=ownership,
        sort_by=sort_by,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    limit: int | Unset = 25,
) -> Response[Error | GetListDesignResponse]:
    """Lists metadata for all the designs in a Canva user's
    [projects](https://www.canva.com/help/find-designs-and-folders/). You can also:

    - Use search terms to filter the listed designs.
    - Show designs either created by, or shared with the user.
    - Sort the results.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetListDesignResponse]
    """

    kwargs = _get_kwargs(
        query=query,
        continuation=continuation,
        ownership=ownership,
        sort_by=sort_by,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    query: str | Unset = UNSET,
    continuation: str | Unset = UNSET,
    ownership: OwnershipType | Unset = UNSET,
    sort_by: SortByType | Unset = UNSET,
    limit: int | Unset = 25,
) -> Error | GetListDesignResponse | None:
    """Lists metadata for all the designs in a Canva user's
    [projects](https://www.canva.com/help/find-designs-and-folders/). You can also:

    - Use search terms to filter the listed designs.
    - Show designs either created by, or shared with the user.
    - Sort the results.

    Args:
        query (str | Unset):
        continuation (str | Unset):
        ownership (OwnershipType | Unset):
        sort_by (SortByType | Unset):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetListDesignResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            query=query,
            continuation=continuation,
            ownership=ownership,
            sort_by=sort_by,
            limit=limit,
        )
    ).parsed
