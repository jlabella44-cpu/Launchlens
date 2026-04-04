from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_design_resize_job_response import GetDesignResizeJobResponse
from ...types import Response


def _get_kwargs(
    job_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/resizes/{job_id}".format(
            job_id=quote(str(job_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetDesignResizeJobResponse:
    if response.status_code == 200:
        response_200 = GetDesignResizeJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetDesignResizeJobResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    job_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignResizeJobResponse]:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Gets the result of a design resize job that was created using the [Create design resize
    job API](https://www.canva.dev/docs/connect/api-reference/resizes/create-design-resize-job/).

    If the job is successful, the response includes a summary of the new resized design, including its
    metadata.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status.
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignResizeJobResponse]
    """

    kwargs = _get_kwargs(
        job_id=job_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    job_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetDesignResizeJobResponse | None:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Gets the result of a design resize job that was created using the [Create design resize
    job API](https://www.canva.dev/docs/connect/api-reference/resizes/create-design-resize-job/).

    If the job is successful, the response includes a summary of the new resized design, including its
    metadata.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status.
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignResizeJobResponse
    """

    return sync_detailed(
        job_id=job_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    job_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignResizeJobResponse]:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Gets the result of a design resize job that was created using the [Create design resize
    job API](https://www.canva.dev/docs/connect/api-reference/resizes/create-design-resize-job/).

    If the job is successful, the response includes a summary of the new resized design, including its
    metadata.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status.
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignResizeJobResponse]
    """

    kwargs = _get_kwargs(
        job_id=job_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    job_id: str,
    *,
    client: AuthenticatedClient,
) -> Error | GetDesignResizeJobResponse | None:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Gets the result of a design resize job that was created using the [Create design resize
    job API](https://www.canva.dev/docs/connect/api-reference/resizes/create-design-resize-job/).

    If the job is successful, the response includes a summary of the new resized design, including its
    metadata.

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status.
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignResizeJobResponse
    """

    return (
        await asyncio_detailed(
            job_id=job_id,
            client=client,
        )
    ).parsed
