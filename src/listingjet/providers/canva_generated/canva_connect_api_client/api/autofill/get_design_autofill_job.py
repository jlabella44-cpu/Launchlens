from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_design_autofill_job_response import GetDesignAutofillJobResponse
from ...types import Response


def _get_kwargs(
    job_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/autofills/{job_id}".format(
            job_id=quote(str(job_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetDesignAutofillJobResponse:
    if response.status_code == 200:
        response_200 = GetDesignAutofillJobResponse.from_dict(response.json())

        return response_200

    if response.status_code == 403:
        response_403 = Error.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())

        return response_404

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetDesignAutofillJobResponse]:
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
) -> Response[Error | GetDesignAutofillJobResponse]:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get the result of a design autofill job that was created using the [Create design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignAutofillJobResponse]
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
) -> Error | GetDesignAutofillJobResponse | None:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get the result of a design autofill job that was created using the [Create design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignAutofillJobResponse
    """

    return sync_detailed(
        job_id=job_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    job_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Error | GetDesignAutofillJobResponse]:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get the result of a design autofill job that was created using the [Create design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetDesignAutofillJobResponse]
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
) -> Error | GetDesignAutofillJobResponse | None:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Get the result of a design autofill job that was created using the [Create design autofill job
    API](https://www.canva.dev/docs/connect/api-reference/autofills/create-design-autofill-job/).

    You might need to make multiple requests to this endpoint until you get a `success` or `failed`
    status. For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).

    Args:
        job_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetDesignAutofillJobResponse
    """

    return (
        await asyncio_detailed(
            job_id=job_id,
            client=client,
        )
    ).parsed
