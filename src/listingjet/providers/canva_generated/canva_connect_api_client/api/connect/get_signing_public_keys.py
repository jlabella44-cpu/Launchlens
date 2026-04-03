from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.get_signing_public_keys_response import GetSigningPublicKeysResponse
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/connect/keys",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | GetSigningPublicKeysResponse:
    if response.status_code == 200:
        response_200 = GetSigningPublicKeysResponse.from_dict(response.json())

        return response_200

    response_default = Error.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | GetSigningPublicKeysResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | GetSigningPublicKeysResponse]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    The Keys API (`connect/keys`) is a security measure you can use to verify the authenticity
    of webhooks you receive from Canva Connect. The Keys API returns a
    [JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517#section-2), which you can use to
    decrypt the webhook signature and verify it came from Canva and not a potentially malicious
    actor. This helps to protect your systems from
    [Replay attacks](https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/).

    The keys returned by the Keys API can rotate. We recommend you cache the keys you receive
    from this API where possible, and only access this API when you receive a webhook signed
    with an unrecognized key. This allows you to verify webhooks quicker than accessing this API
    every time you receive a webhook.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetSigningPublicKeysResponse]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> Error | GetSigningPublicKeysResponse | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    The Keys API (`connect/keys`) is a security measure you can use to verify the authenticity
    of webhooks you receive from Canva Connect. The Keys API returns a
    [JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517#section-2), which you can use to
    decrypt the webhook signature and verify it came from Canva and not a potentially malicious
    actor. This helps to protect your systems from
    [Replay attacks](https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/).

    The keys returned by the Keys API can rotate. We recommend you cache the keys you receive
    from this API where possible, and only access this API when you receive a webhook signed
    with an unrecognized key. This allows you to verify webhooks quicker than accessing this API
    every time you receive a webhook.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetSigningPublicKeysResponse
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[Error | GetSigningPublicKeysResponse]:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    The Keys API (`connect/keys`) is a security measure you can use to verify the authenticity
    of webhooks you receive from Canva Connect. The Keys API returns a
    [JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517#section-2), which you can use to
    decrypt the webhook signature and verify it came from Canva and not a potentially malicious
    actor. This helps to protect your systems from
    [Replay attacks](https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/).

    The keys returned by the Keys API can rotate. We recommend you cache the keys you receive
    from this API where possible, and only access this API when you receive a webhook signed
    with an unrecognized key. This allows you to verify webhooks quicker than accessing this API
    every time you receive a webhook.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetSigningPublicKeysResponse]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> Error | GetSigningPublicKeysResponse | None:
    """<Warning>

    This API is currently provided as a preview. Be aware of the following:

    - There might be unannounced breaking changes.
    - Any breaking changes to preview APIs won't produce a new [API
    version](https://www.canva.dev/docs/connect/versions/).
    - Public integrations that use preview APIs will not pass the review process, and can't be made
    available to all Canva users.

    </Warning>

    The Keys API (`connect/keys`) is a security measure you can use to verify the authenticity
    of webhooks you receive from Canva Connect. The Keys API returns a
    [JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517#section-2), which you can use to
    decrypt the webhook signature and verify it came from Canva and not a potentially malicious
    actor. This helps to protect your systems from
    [Replay attacks](https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/).

    The keys returned by the Keys API can rotate. We recommend you cache the keys you receive
    from this API where possible, and only access this API when you receive a webhook signed
    with an unrecognized key. This allows you to verify webhooks quicker than accessing this API
    every time you receive a webhook.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetSigningPublicKeysResponse
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
