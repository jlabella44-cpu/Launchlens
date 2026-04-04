from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_url_import_job_request import CreateUrlImportJobRequest
from ...models.create_url_import_job_response import CreateUrlImportJobResponse
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    *,
    body: CreateUrlImportJobRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/url-imports",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateUrlImportJobResponse | Error:
    if response.status_code == 200:
        response_200 = CreateUrlImportJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateUrlImportJobResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateUrlImportJobRequest,
) -> Response[CreateUrlImportJobResponse | Error]:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to import an external file from a URL as a new design in
    Canva.

    Supported file types for imports are listed in [Design imports
    overview](https://www.canva.dev/docs/connect/api-reference/design-imports/#supported-file-types).

    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of design import jobs created with this API using the
    [Get URL import job API](https://www.canva.dev/docs/connect/api-reference/design-imports/get-url-
    import-job/).

    </Note>

    Args:
        body (CreateUrlImportJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateUrlImportJobResponse | Error]
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
    body: CreateUrlImportJobRequest,
) -> CreateUrlImportJobResponse | Error | None:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to import an external file from a URL as a new design in
    Canva.

    Supported file types for imports are listed in [Design imports
    overview](https://www.canva.dev/docs/connect/api-reference/design-imports/#supported-file-types).

    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of design import jobs created with this API using the
    [Get URL import job API](https://www.canva.dev/docs/connect/api-reference/design-imports/get-url-
    import-job/).

    </Note>

    Args:
        body (CreateUrlImportJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateUrlImportJobResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateUrlImportJobRequest,
) -> Response[CreateUrlImportJobResponse | Error]:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to import an external file from a URL as a new design in
    Canva.

    Supported file types for imports are listed in [Design imports
    overview](https://www.canva.dev/docs/connect/api-reference/design-imports/#supported-file-types).

    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of design import jobs created with this API using the
    [Get URL import job API](https://www.canva.dev/docs/connect/api-reference/design-imports/get-url-
    import-job/).

    </Note>

    Args:
        body (CreateUrlImportJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateUrlImportJobResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateUrlImportJobRequest,
) -> CreateUrlImportJobResponse | Error | None:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to import an external file from a URL as a new design in
    Canva.

    Supported file types for imports are listed in [Design imports
    overview](https://www.canva.dev/docs/connect/api-reference/design-imports/#supported-file-types).

    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of design import jobs created with this API using the
    [Get URL import job API](https://www.canva.dev/docs/connect/api-reference/design-imports/get-url-
    import-job/).

    </Note>

    Args:
        body (CreateUrlImportJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateUrlImportJobResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
