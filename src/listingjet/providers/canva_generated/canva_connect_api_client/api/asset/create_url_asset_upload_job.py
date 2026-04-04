from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_url_asset_upload_job_request import CreateUrlAssetUploadJobRequest
from ...models.create_url_asset_upload_job_response import CreateUrlAssetUploadJobResponse
from ...models.error import Error
from ...types import Response


def _get_kwargs(
    *,
    body: CreateUrlAssetUploadJobRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/url-asset-uploads",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateUrlAssetUploadJobResponse | Error:
    if response.status_code == 200:
        response_200 = CreateUrlAssetUploadJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateUrlAssetUploadJobResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateUrlAssetUploadJobRequest,
) -> Response[CreateUrlAssetUploadJobResponse | Error]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset from a URL to the user's content library.
    Supported file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    <Note>
     Uploading a video asset from a URL is limited to a maximum 100MB file size. For importing larger
    video files, use the [Create asset upload job API](https://www.canva.dev/docs/connect/api-
    reference/assets/create-asset-upload-job/).
    </Note>

    <Note>
    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job via URL API](https://www.canva.dev/docs/connect/api-reference/assets/get-url-
    asset-upload-job/).
    </Note>

    Args:
        body (CreateUrlAssetUploadJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateUrlAssetUploadJobResponse | Error]
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
    body: CreateUrlAssetUploadJobRequest,
) -> CreateUrlAssetUploadJobResponse | Error | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset from a URL to the user's content library.
    Supported file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    <Note>
     Uploading a video asset from a URL is limited to a maximum 100MB file size. For importing larger
    video files, use the [Create asset upload job API](https://www.canva.dev/docs/connect/api-
    reference/assets/create-asset-upload-job/).
    </Note>

    <Note>
    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job via URL API](https://www.canva.dev/docs/connect/api-reference/assets/get-url-
    asset-upload-job/).
    </Note>

    Args:
        body (CreateUrlAssetUploadJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateUrlAssetUploadJobResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateUrlAssetUploadJobRequest,
) -> Response[CreateUrlAssetUploadJobResponse | Error]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset from a URL to the user's content library.
    Supported file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    <Note>
     Uploading a video asset from a URL is limited to a maximum 100MB file size. For importing larger
    video files, use the [Create asset upload job API](https://www.canva.dev/docs/connect/api-
    reference/assets/create-asset-upload-job/).
    </Note>

    <Note>
    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job via URL API](https://www.canva.dev/docs/connect/api-reference/assets/get-url-
    asset-upload-job/).
    </Note>

    Args:
        body (CreateUrlAssetUploadJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateUrlAssetUploadJobResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateUrlAssetUploadJobRequest,
) -> CreateUrlAssetUploadJobResponse | Error | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to upload an asset from a URL to the user's content library.
    Supported file types for assets are listed in the [Assets API
    overview](https://www.canva.dev/docs/connect/api-reference/assets/).

    <Note>
     Uploading a video asset from a URL is limited to a maximum 100MB file size. For importing larger
    video files, use the [Create asset upload job API](https://www.canva.dev/docs/connect/api-
    reference/assets/create-asset-upload-job/).
    </Note>

    <Note>
    For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of asset upload jobs created with this API using the
    [Get asset upload job via URL API](https://www.canva.dev/docs/connect/api-reference/assets/get-url-
    asset-upload-job/).
    </Note>

    Args:
        body (CreateUrlAssetUploadJobRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateUrlAssetUploadJobResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
