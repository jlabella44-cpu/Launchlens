from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_design_export_formats_response import GetDesignExportFormatsResponse
from ...types import Response


def _get_kwargs(
    design_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/designs/{design_id}/export-formats".format(
            design_id=quote(str(design_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetDesignExportFormatsResponse:
    if response.status_code == 200:
        response_200 = GetDesignExportFormatsResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetDesignExportFormatsResponse]:
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
) -> Response[Error | GetDesignExportFormatsResponse]:
    """Lists the available file formats for [exporting a design](https://www.canva.dev/docs/connect/api-
    reference/exports/create-design-export-job/).

    <Note>
    The available export formats depend on the design type and the types of pages in the design.
    In general, the available export formats returned are only those that are supported by every page
    type in the design.
    </Note>

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignExportFormatsResponse]
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
) -> Error | GetDesignExportFormatsResponse | None:
    """Lists the available file formats for [exporting a design](https://www.canva.dev/docs/connect/api-
    reference/exports/create-design-export-job/).

    <Note>
    The available export formats depend on the design type and the types of pages in the design.
    In general, the available export formats returned are only those that are supported by every page
    type in the design.
    </Note>

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignExportFormatsResponse
    """

    return sync_detailed(
        design_id=design_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    design_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignExportFormatsResponse]:
    """Lists the available file formats for [exporting a design](https://www.canva.dev/docs/connect/api-
    reference/exports/create-design-export-job/).

    <Note>
    The available export formats depend on the design type and the types of pages in the design.
    In general, the available export formats returned are only those that are supported by every page
    type in the design.
    </Note>

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignExportFormatsResponse]
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
) -> Error | GetDesignExportFormatsResponse | None:
    """Lists the available file formats for [exporting a design](https://www.canva.dev/docs/connect/api-
    reference/exports/create-design-export-job/).

    <Note>
    The available export formats depend on the design type and the types of pages in the design.
    In general, the available export formats returned are only those that are supported by every page
    type in the design.
    </Note>

    Args:
        design_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignExportFormatsResponse
    """

    return (
        await asyncio_detailed(
            design_id=design_id,
            client=client,
        )
    ).parsed
