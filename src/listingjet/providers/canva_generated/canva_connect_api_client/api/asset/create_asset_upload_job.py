from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_asset_upload_job_response import CreateAssetUploadJobResponse
from ...models.error import Error
from ...types import File, Response


def _get_kwargs(
    *,
    body: File,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/asset-uploads",
    }

    _kwargs["content"] = body.payload

    headers["Content-Type"] = "application/octet-stream"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateAssetUploadJobResponse | Error:
    if response.status_code == 200:
        response_200 = CreateAssetUploadJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateAssetUploadJobResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: File,
) -> Response[CreateAssetUploadJobResponse | Error]:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset to the user's content library. Supported
    file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    The request format for this endpoint is an `application/octet-stream` body of bytes. Attach
    information about the upload using an `Asset-Upload-Metadata` header.


    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job API](https://www.canva.dev/docs/connect/api-reference/assets/get-asset-upload-
    job/).

    </Note>

    Args:
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAssetUploadJobResponse | Error]
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
    body: File,
) -> CreateAssetUploadJobResponse | Error | None:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset to the user's content library. Supported
    file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    The request format for this endpoint is an `application/octet-stream` body of bytes. Attach
    information about the upload using an `Asset-Upload-Metadata` header.


    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job API](https://www.canva.dev/docs/connect/api-reference/assets/get-asset-upload-
    job/).

    </Note>

    Args:
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAssetUploadJobResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: File,
) -> Response[CreateAssetUploadJobResponse | Error]:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset to the user's content library. Supported
    file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    The request format for this endpoint is an `application/octet-stream` body of bytes. Attach
    information about the upload using an `Asset-Upload-Metadata` header.


    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job API](https://www.canva.dev/docs/connect/api-reference/assets/get-asset-upload-
    job/).

    </Note>

    Args:
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateAssetUploadJobResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: File,
) -> CreateAssetUploadJobResponse | Error | None:
    """Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset to the user's content library. Supported
    file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    The request format for this endpoint is an `application/octet-stream` body of bytes. Attach
    information about the upload using an `Asset-Upload-Metadata` header.


    <Note>

    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job API](https://www.canva.dev/docs/connect/api-reference/assets/get-asset-upload-
    job/).

    </Note>

    Args:
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateAssetUploadJobResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
