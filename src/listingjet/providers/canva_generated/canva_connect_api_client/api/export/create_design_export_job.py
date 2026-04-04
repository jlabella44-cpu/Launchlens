from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_design_export_job_request import CreateDesignExportJobRequest
from ...models.create_design_export_job_response import CreateDesignExportJobResponse
from ...models.error import Error
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: CreateDesignExportJobRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/exports",
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateDesignExportJobResponse | Error:
    if response.status_code == 200:
        response_200 = CreateDesignExportJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateDesignExportJobResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateDesignExportJobRequest | Unset = UNSET,
) -> Response[CreateDesignExportJobResponse | Error]:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to export a file from Canva. Once the exported file is
    generated, you can download
    it using the URL(s) provided. The download URLs are only valid for 24 hours.

    The request requires the design ID and the exported file format type.

    Supported file formats (and export file type values): JPG (`jpg`), PNG (`png`), GIF (`gif`),
    Microsoft PowerPoint (`pptx`), MP4 (`mp4`), PDF (`pdf`), HTML bundle (`html_bundle`), and standalone
    HTML (`html_standalone`).

    <Note>

    This endpoint has the following additional rate limits:

      - **Integration throttle:** Each integration can export a maximum of 750 times per 5-minute
    window, and 5,000 times per 24-hour window.
      - **Document throttle:** Each document can be exported a maximum of 75 times per 5-minute window.
      - **User throttle:** Each user can export a maximum of 75 times per 5-minute window, and 500 times
    per 24-hour window.

    </Note>
    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of export jobs created with this API using the [Get
    design export job API](https://www.canva.dev/docs/connect/api-reference/exports/get-design-export-
    job/).

    </Note>

    Args:
        body (CreateDesignExportJobRequest | Unset): Body parameters for starting an export job
            for a design.
            It must include a design ID, and one of the supported export formats. Example:
            {'design_id': 'DAVZr1z5464', 'format': {'type': 'pdf', 'size': 'a4', 'pages': [2, 3, 4]}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignExportJobResponse | Error]
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
    body: CreateDesignExportJobRequest | Unset = UNSET,
) -> CreateDesignExportJobResponse | Error | None:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to export a file from Canva. Once the exported file is
    generated, you can download
    it using the URL(s) provided. The download URLs are only valid for 24 hours.

    The request requires the design ID and the exported file format type.

    Supported file formats (and export file type values): JPG (`jpg`), PNG (`png`), GIF (`gif`),
    Microsoft PowerPoint (`pptx`), MP4 (`mp4`), PDF (`pdf`), HTML bundle (`html_bundle`), and standalone
    HTML (`html_standalone`).

    <Note>

    This endpoint has the following additional rate limits:

      - **Integration throttle:** Each integration can export a maximum of 750 times per 5-minute
    window, and 5,000 times per 24-hour window.
      - **Document throttle:** Each document can be exported a maximum of 75 times per 5-minute window.
      - **User throttle:** Each user can export a maximum of 75 times per 5-minute window, and 500 times
    per 24-hour window.

    </Note>
    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of export jobs created with this API using the [Get
    design export job API](https://www.canva.dev/docs/connect/api-reference/exports/get-design-export-
    job/).

    </Note>

    Args:
        body (CreateDesignExportJobRequest | Unset): Body parameters for starting an export job
            for a design.
            It must include a design ID, and one of the supported export formats. Example:
            {'design_id': 'DAVZr1z5464', 'format': {'type': 'pdf', 'size': 'a4', 'pages': [2, 3, 4]}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignExportJobResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateDesignExportJobRequest | Unset = UNSET,
) -> Response[CreateDesignExportJobResponse | Error]:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to export a file from Canva. Once the exported file is
    generated, you can download
    it using the URL(s) provided. The download URLs are only valid for 24 hours.

    The request requires the design ID and the exported file format type.

    Supported file formats (and export file type values): JPG (`jpg`), PNG (`png`), GIF (`gif`),
    Microsoft PowerPoint (`pptx`), MP4 (`mp4`), PDF (`pdf`), HTML bundle (`html_bundle`), and standalone
    HTML (`html_standalone`).

    <Note>

    This endpoint has the following additional rate limits:

      - **Integration throttle:** Each integration can export a maximum of 750 times per 5-minute
    window, and 5,000 times per 24-hour window.
      - **Document throttle:** Each document can be exported a maximum of 75 times per 5-minute window.
      - **User throttle:** Each user can export a maximum of 75 times per 5-minute window, and 500 times
    per 24-hour window.

    </Note>
    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of export jobs created with this API using the [Get
    design export job API](https://www.canva.dev/docs/connect/api-reference/exports/get-design-export-
    job/).

    </Note>

    Args:
        body (CreateDesignExportJobRequest | Unset): Body parameters for starting an export job
            for a design.
            It must include a design ID, and one of the supported export formats. Example:
            {'design_id': 'DAVZr1z5464', 'format': {'type': 'pdf', 'size': 'a4', 'pages': [2, 3, 4]}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignExportJobResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateDesignExportJobRequest | Unset = UNSET,
) -> CreateDesignExportJobResponse | Error | None:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to export a file from Canva. Once the exported file is
    generated, you can download
    it using the URL(s) provided. The download URLs are only valid for 24 hours.

    The request requires the design ID and the exported file format type.

    Supported file formats (and export file type values): JPG (`jpg`), PNG (`png`), GIF (`gif`),
    Microsoft PowerPoint (`pptx`), MP4 (`mp4`), PDF (`pdf`), HTML bundle (`html_bundle`), and standalone
    HTML (`html_standalone`).

    <Note>

    This endpoint has the following additional rate limits:

      - **Integration throttle:** Each integration can export a maximum of 750 times per 5-minute
    window, and 5,000 times per 24-hour window.
      - **Document throttle:** Each document can be exported a maximum of 75 times per 5-minute window.
      - **User throttle:** Each user can export a maximum of 75 times per 5-minute window, and 500 times
    per 24-hour window.

    </Note>
    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of export jobs created with this API using the [Get
    design export job API](https://www.canva.dev/docs/connect/api-reference/exports/get-design-export-
    job/).

    </Note>

    Args:
        body (CreateDesignExportJobRequest | Unset): Body parameters for starting an export job
            for a design.
            It must include a design ID, and one of the supported export formats. Example:
            {'design_id': 'DAVZr1z5464', 'format': {'type': 'pdf', 'size': 'a4', 'pages': [2, 3, 4]}}.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignExportJobResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
