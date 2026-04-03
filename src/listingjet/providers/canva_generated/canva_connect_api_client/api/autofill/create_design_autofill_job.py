from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_design_autofill_job_request import CreateDesignAutofillJobRequest
from ...models.create_design_autofill_job_response import CreateDesignAutofillJobResponse
from ...models.error import Error
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: CreateDesignAutofillJobRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/autofills",
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateDesignAutofillJobResponse | Error:
    if response.status_code == 200:
        response_200 = CreateDesignAutofillJobResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

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
) -> Response[CreateDesignAutofillJobResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateDesignAutofillJobRequest | Unset = UNSET,
) -> Response[CreateDesignAutofillJobResponse | Error]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to autofill a Canva design using a brand template and input
    data.

    To get a list of input data fields, use the [Get brand template dataset
    API](https://www.canva.dev/docs/connect/api-reference/brand-templates/get-brand-template-dataset/).

    Available data field types to autofill include:

    - Images
    - Text
    - Charts

      WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    NOTE: For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of autofill jobs created with this API using the [Get
    design autofill job API](https://www.canva.dev/docs/connect/api-reference/autofills/get-design-
    autofill-job/).

    Args:
        body (CreateDesignAutofillJobRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignAutofillJobResponse | Error]
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
    body: CreateDesignAutofillJobRequest | Unset = UNSET,
) -> CreateDesignAutofillJobResponse | Error | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to autofill a Canva design using a brand template and input
    data.

    To get a list of input data fields, use the [Get brand template dataset
    API](https://www.canva.dev/docs/connect/api-reference/brand-templates/get-brand-template-dataset/).

    Available data field types to autofill include:

    - Images
    - Text
    - Charts

      WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    NOTE: For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of autofill jobs created with this API using the [Get
    design autofill job API](https://www.canva.dev/docs/connect/api-reference/autofills/get-design-
    autofill-job/).

    Args:
        body (CreateDesignAutofillJobRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignAutofillJobResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateDesignAutofillJobRequest | Unset = UNSET,
) -> Response[CreateDesignAutofillJobResponse | Error]:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to autofill a Canva design using a brand template and input
    data.

    To get a list of input data fields, use the [Get brand template dataset
    API](https://www.canva.dev/docs/connect/api-reference/brand-templates/get-brand-template-dataset/).

    Available data field types to autofill include:

    - Images
    - Text
    - Charts

      WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    NOTE: For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of autofill jobs created with this API using the [Get
    design autofill job API](https://www.canva.dev/docs/connect/api-reference/autofills/get-design-
    autofill-job/).

    Args:
        body (CreateDesignAutofillJobRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignAutofillJobResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateDesignAutofillJobRequest | Unset = UNSET,
) -> CreateDesignAutofillJobResponse | Error | None:
    """WARNING: Brand templates were migrated to use a new ID format in September 2025. If your integration
    stores brand template IDs, you'll need to migrate to use the new IDs. Old brand template IDs will
    continue to be accepted for 6 months to give you time to migrate to the new IDs.

    AVAILABILITY: To use this API, your integration must act on behalf of a user that's a member of a
    [Canva Enterprise](https://www.canva.com/enterprise/) organization.

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints) to autofill a Canva design using a brand template and input
    data.

    To get a list of input data fields, use the [Get brand template dataset
    API](https://www.canva.dev/docs/connect/api-reference/brand-templates/get-brand-template-dataset/).

    Available data field types to autofill include:

    - Images
    - Text
    - Charts

      WARNING: Chart data fields are a [preview feature](https://www.canva.dev/docs/connect/#preview-
    apis). There might be unannounced breaking changes to this feature which won't produce a new API
    version.

    NOTE: For more information on the workflow for using asynchronous jobs, see [API requests and
    responses](https://www.canva.dev/docs/connect/api-requests-responses/#asynchronous-job-endpoints).
    You can check the status and get the results of autofill jobs created with this API using the [Get
    design autofill job API](https://www.canva.dev/docs/connect/api-reference/autofills/get-design-
    autofill-job/).

    Args:
        body (CreateDesignAutofillJobRequest | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignAutofillJobResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
