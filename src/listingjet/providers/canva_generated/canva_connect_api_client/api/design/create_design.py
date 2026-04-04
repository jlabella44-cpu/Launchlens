from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_design_response import CreateDesignResponse
from ...models.design_type_create_design_request import DesignTypeCreateDesignRequest
from ...models.error import Error
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: DesignTypeCreateDesignRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/designs",
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> CreateDesignResponse | Error:
    if response.status_code == 200:
        response_200 = CreateDesignResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateDesignResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: DesignTypeCreateDesignRequest | Unset = UNSET,
) -> Response[CreateDesignResponse | Error]:
    """Creates a new Canva design. To create a new design, you can either:

    - Use a preset design type.
    - Set height and width dimensions for a custom design.

    Additionally, you can also provide the `asset_id` of an asset in the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) to add to the new design.
    Currently, this only supports image assets. To list the assets in a folder in the user's projects,
    use the [List folder items API](https://www.canva.dev/docs/connect/api-reference/folders/list-
    folder-items/).

    NOTE: Blank designs created with this API are automatically deleted if they're not edited within 7
    days. These blank designs bypass the user's Canva trash and are permanently deleted.

    Args:
        body (DesignTypeCreateDesignRequest | Unset): Create a design by specifying the design
            type and/or an asset.
            At least one of `design_type` or `asset_id` must be defined.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: DesignTypeCreateDesignRequest | Unset = UNSET,
) -> CreateDesignResponse | Error | None:
    """Creates a new Canva design. To create a new design, you can either:

    - Use a preset design type.
    - Set height and width dimensions for a custom design.

    Additionally, you can also provide the `asset_id` of an asset in the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) to add to the new design.
    Currently, this only supports image assets. To list the assets in a folder in the user's projects,
    use the [List folder items API](https://www.canva.dev/docs/connect/api-reference/folders/list-
    folder-items/).

    NOTE: Blank designs created with this API are automatically deleted if they're not edited within 7
    days. These blank designs bypass the user's Canva trash and are permanently deleted.

    Args:
        body (DesignTypeCreateDesignRequest | Unset): Create a design by specifying the design
            type and/or an asset.
            At least one of `design_type` or `asset_id` must be defined.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: DesignTypeCreateDesignRequest | Unset = UNSET,
) -> Response[CreateDesignResponse | Error]:
    """Creates a new Canva design. To create a new design, you can either:

    - Use a preset design type.
    - Set height and width dimensions for a custom design.

    Additionally, you can also provide the `asset_id` of an asset in the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) to add to the new design.
    Currently, this only supports image assets. To list the assets in a folder in the user's projects,
    use the [List folder items API](https://www.canva.dev/docs/connect/api-reference/folders/list-
    folder-items/).

    NOTE: Blank designs created with this API are automatically deleted if they're not edited within 7
    days. These blank designs bypass the user's Canva trash and are permanently deleted.

    Args:
        body (DesignTypeCreateDesignRequest | Unset): Create a design by specifying the design
            type and/or an asset.
            At least one of `design_type` or `asset_id` must be defined.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: DesignTypeCreateDesignRequest | Unset = UNSET,
) -> CreateDesignResponse | Error | None:
    """Creates a new Canva design. To create a new design, you can either:

    - Use a preset design type.
    - Set height and width dimensions for a custom design.

    Additionally, you can also provide the `asset_id` of an asset in the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) to add to the new design.
    Currently, this only supports image assets. To list the assets in a folder in the user's projects,
    use the [List folder items API](https://www.canva.dev/docs/connect/api-reference/folders/list-
    folder-items/).

    NOTE: Blank designs created with this API are automatically deleted if they're not edited within 7
    days. These blank designs bypass the user's Canva trash and are permanently deleted.

    Args:
        body (DesignTypeCreateDesignRequest | Unset): Create a design by specifying the design
            type and/or an asset.
            At least one of `design_type` or `asset_id` must be defined.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
