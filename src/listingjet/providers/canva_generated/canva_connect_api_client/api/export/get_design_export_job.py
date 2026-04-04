from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_design_export_job_response import GetDesignExportJobResponse
from ...types import Response


def _get_kwargs(
    export_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/exports/{export_id}".format(
            export_id=quote(str(export_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetDesignExportJobResponse:
    if response.status_code == 200:
        response_200 = GetDesignExportJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetDesignExportJobResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    export_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignExportJobResponse]:
    """Gets the result of a design export job that was created using the [Create design export job
    API](https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/).

    If the job is successful, the response includes an array
    of download URLs. Depending on the design type and export format, there is a download URL for each
    page in the design. The download URLs are only valid for 24 hours.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        export_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignExportJobResponse]
    """

    kwargs = _get_kwargs(
        export_id=export_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    export_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetDesignExportJobResponse | None:
    """Gets the result of a design export job that was created using the [Create design export job
    API](https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/).

    If the job is successful, the response includes an array
    of download URLs. Depending on the design type and export format, there is a download URL for each
    page in the design. The download URLs are only valid for 24 hours.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        export_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignExportJobResponse
    """

    return sync_detailed(
        export_id=export_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    export_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignExportJobResponse]:
    """Gets the result of a design export job that was created using the [Create design export job
    API](https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/).

    If the job is successful, the response includes an array
    of download URLs. Depending on the design type and export format, there is a download URL for each
    page in the design. The download URLs are only valid for 24 hours.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        export_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignExportJobResponse]
    """

    kwargs = _get_kwargs(
        export_id=export_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    export_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetDesignExportJobResponse | None:
    """Gets the result of a design export job that was created using the [Create design export job
    API](https://www.canva.dev/docs/connect/api-reference/exports/create-design-export-job/).

    If the job is successful, the response includes an array
    of download URLs. Depending on the design type and export format, there is a download URL for each
    page in the design. The download URLs are only valid for 24 hours.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        export_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignExportJobResponse
    """

    return (
        await asyncio_detailed(
            export_id=export_id,
            client=client,
        )
    ).parsed
