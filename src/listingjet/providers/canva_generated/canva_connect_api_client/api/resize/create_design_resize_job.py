from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.create_design_resize_job_request import CreateDesignResizeJobRequest
from ...models.create_design_resize_job_response import CreateDesignResizeJobResponse
from ...models.error import Error
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: CreateDesignResizeJobRequest | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/resizes",
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CreateDesignResizeJobResponse | Error:
    if response.status_code == 200:
        response_200 = CreateDesignResizeJobResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CreateDesignResizeJobResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateDesignResizeJobRequest | Unset = UNSET,
) -> Response[CreateDesignResizeJobResponse | Error]:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints)
    to create a resized copy of a design. The new resized design is
    added to the top level of the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) (`root` folder).

    To resize a design into a new design, you can either:

      - Use a preset design type.
      - Set height and width dimensions for a custom design.

    Note the following behaviors and restrictions when resizing designs:
    - Designs can be resized to a maximum area of 25,000,000 pixels squared.
    - Resizing designs using the Connect API always creates a new design. In-place resizing is currently
    not available in the Connect API, but can be done in the Canva UI.
    - Resizing a multi-page design results in all pages of the design being resized. Resizing a section
    of a design is only available in the Canva UI.
    - [Canva docs](https://www.canva.com/create/documents/) can't be resized, and other design types
    can't be resized to a Canva doc.
    - Canva Code designs can't be resized, and other design types can't be resized to a Canva Code
    design.

    <Note>
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).
    You can check the status and get the results of resize jobs created with this API using the
    [Get design resize job API](https://www.canva.dev/docs/connect/api-reference/resizes/get-design-
    resize-job/).
    </Note>

    Args:
        body (CreateDesignResizeJobRequest | Unset): Body parameters for starting a resize job for
            a design.
            It must include a design ID, and one of the supported design type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignResizeJobResponse | Error]
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
    body: CreateDesignResizeJobRequest | Unset = UNSET,
) -> CreateDesignResizeJobResponse | Error | None:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints)
    to create a resized copy of a design. The new resized design is
    added to the top level of the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) (`root` folder).

    To resize a design into a new design, you can either:

      - Use a preset design type.
      - Set height and width dimensions for a custom design.

    Note the following behaviors and restrictions when resizing designs:
    - Designs can be resized to a maximum area of 25,000,000 pixels squared.
    - Resizing designs using the Connect API always creates a new design. In-place resizing is currently
    not available in the Connect API, but can be done in the Canva UI.
    - Resizing a multi-page design results in all pages of the design being resized. Resizing a section
    of a design is only available in the Canva UI.
    - [Canva docs](https://www.canva.com/create/documents/) can't be resized, and other design types
    can't be resized to a Canva doc.
    - Canva Code designs can't be resized, and other design types can't be resized to a Canva Code
    design.

    <Note>
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).
    You can check the status and get the results of resize jobs created with this API using the
    [Get design resize job API](https://www.canva.dev/docs/connect/api-reference/resizes/get-design-
    resize-job/).
    </Note>

    Args:
        body (CreateDesignResizeJobRequest | Unset): Body parameters for starting a resize job for
            a design.
            It must include a design ID, and one of the supported design type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignResizeJobResponse | Error
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: CreateDesignResizeJobRequest | Unset = UNSET,
) -> Response[CreateDesignResizeJobResponse | Error]:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints)
    to create a resized copy of a design. The new resized design is
    added to the top level of the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) (`root` folder).

    To resize a design into a new design, you can either:

      - Use a preset design type.
      - Set height and width dimensions for a custom design.

    Note the following behaviors and restrictions when resizing designs:
    - Designs can be resized to a maximum area of 25,000,000 pixels squared.
    - Resizing designs using the Connect API always creates a new design. In-place resizing is currently
    not available in the Connect API, but can be done in the Canva UI.
    - Resizing a multi-page design results in all pages of the design being resized. Resizing a section
    of a design is only available in the Canva UI.
    - [Canva docs](https://www.canva.com/create/documents/) can't be resized, and other design types
    can't be resized to a Canva doc.
    - Canva Code designs can't be resized, and other design types can't be resized to a Canva Code
    design.

    <Note>
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).
    You can check the status and get the results of resize jobs created with this API using the
    [Get design resize job API](https://www.canva.dev/docs/connect/api-reference/resizes/get-design-
    resize-job/).
    </Note>

    Args:
        body (CreateDesignResizeJobRequest | Unset): Body parameters for starting a resize job for
            a design.
            It must include a design ID, and one of the supported design type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CreateDesignResizeJobResponse | Error]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: CreateDesignResizeJobRequest | Unset = UNSET,
) -> CreateDesignResizeJobResponse | Error | None:
    """AVAILABILITY: To use this API, your integration must act on behalf of a user that's on a Canva plan
    with premium features (such as Canva Pro).

    Starts a new [asynchronous job](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints)
    to create a resized copy of a design. The new resized design is
    added to the top level of the user's
    [projects](https://www.canva.com/help/find-designs-and-folders/) (`root` folder).

    To resize a design into a new design, you can either:

      - Use a preset design type.
      - Set height and width dimensions for a custom design.

    Note the following behaviors and restrictions when resizing designs:
    - Designs can be resized to a maximum area of 25,000,000 pixels squared.
    - Resizing designs using the Connect API always creates a new design. In-place resizing is currently
    not available in the Connect API, but can be done in the Canva UI.
    - Resizing a multi-page design results in all pages of the design being resized. Resizing a section
    of a design is only available in the Canva UI.
    - [Canva docs](https://www.canva.com/create/documents/) can't be resized, and other design types
    can't be resized to a Canva doc.
    - Canva Code designs can't be resized, and other design types can't be resized to a Canva Code
    design.

    <Note>
    For more information on the workflow for using asynchronous jobs,
    see [API requests and responses](https://www.canva.dev/docs/connect/api-requests-
    responses/#asynchronous-job-endpoints).
    You can check the status and get the results of resize jobs created with this API using the
    [Get design resize job API](https://www.canva.dev/docs/connect/api-reference/resizes/get-design-
    resize-job/).
    </Note>

    Args:
        body (CreateDesignResizeJobRequest | Unset): Body parameters for starting a resize job for
            a design.
            It must include a design ID, and one of the supported design type.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CreateDesignResizeJobResponse | Error
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
