from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.oauth_error import OauthError
from ...models.revoke_tokens_request import RevokeTokensRequest
from ...models.revoke_tokens_response import RevokeTokensResponse
from ...types import Response


def _get_kwargs(
    *,
    body: RevokeTokensRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/oauth/revoke",
    }

    _kwargs["data"] = body.to_dict()

    headers["Content-Type"] = "application/x-www-form-urlencoded"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | OauthError | RevokeTokensResponse:
    if response.status_code == 200:
        response_200 = RevokeTokensResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = Error.from_dict(response.json())

        return response_401

    response_default = OauthError.from_dict(response.json())

    return response_default


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Error | OauthError | RevokeTokensResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: RevokeTokensRequest,
) -> Response[Error | OauthError | RevokeTokensResponse]:
    """Revoke an access token or a refresh token.

    If you revoke a _refresh token_, be aware that:

    - The refresh token's lineage is also revoked. This means that access tokens created from that
    refresh token are also revoked.
    - The user's consent for your integration is also revoked. This means that the user must go through
    the OAuth process again to use your integration.

    Requests to this endpoint require authentication with your client ID and client secret, using _one_
    of the following methods:

    - **Basic access authentication** (Recommended): For [basic access
    authentication](https://en.wikipedia.org/wiki/Basic_access_authentication), the `{credentials}`
    string must be a Base64 encoded value of `{client id}:{client secret}`.
    - **Body parameters**: Provide your integration's credentials using the `client_id` and
    `client_secret` body parameters.

    This endpoint can't be called from a user's web-browser client because it uses client authentication
    with client secrets. Requests must come from your integration's backend, otherwise they'll be
    blocked by Canva's [Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/en-
    US/docs/Web/HTTP/CORS) policy.

    Args:
        body (RevokeTokensRequest): Supply an access token or refresh token to have its lineage
            revoked.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | OauthError | RevokeTokensResponse]
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
    body: RevokeTokensRequest,
) -> Error | OauthError | RevokeTokensResponse | None:
    """Revoke an access token or a refresh token.

    If you revoke a _refresh token_, be aware that:

    - The refresh token's lineage is also revoked. This means that access tokens created from that
    refresh token are also revoked.
    - The user's consent for your integration is also revoked. This means that the user must go through
    the OAuth process again to use your integration.

    Requests to this endpoint require authentication with your client ID and client secret, using _one_
    of the following methods:

    - **Basic access authentication** (Recommended): For [basic access
    authentication](https://en.wikipedia.org/wiki/Basic_access_authentication), the `{credentials}`
    string must be a Base64 encoded value of `{client id}:{client secret}`.
    - **Body parameters**: Provide your integration's credentials using the `client_id` and
    `client_secret` body parameters.

    This endpoint can't be called from a user's web-browser client because it uses client authentication
    with client secrets. Requests must come from your integration's backend, otherwise they'll be
    blocked by Canva's [Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/en-
    US/docs/Web/HTTP/CORS) policy.

    Args:
        body (RevokeTokensRequest): Supply an access token or refresh token to have its lineage
            revoked.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | OauthError | RevokeTokensResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: RevokeTokensRequest,
) -> Response[Error | OauthError | RevokeTokensResponse]:
    """Revoke an access token or a refresh token.

    If you revoke a _refresh token_, be aware that:

    - The refresh token's lineage is also revoked. This means that access tokens created from that
    refresh token are also revoked.
    - The user's consent for your integration is also revoked. This means that the user must go through
    the OAuth process again to use your integration.

    Requests to this endpoint require authentication with your client ID and client secret, using _one_
    of the following methods:

    - **Basic access authentication** (Recommended): For [basic access
    authentication](https://en.wikipedia.org/wiki/Basic_access_authentication), the `{credentials}`
    string must be a Base64 encoded value of `{client id}:{client secret}`.
    - **Body parameters**: Provide your integration's credentials using the `client_id` and
    `client_secret` body parameters.

    This endpoint can't be called from a user's web-browser client because it uses client authentication
    with client secrets. Requests must come from your integration's backend, otherwise they'll be
    blocked by Canva's [Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/en-
    US/docs/Web/HTTP/CORS) policy.

    Args:
        body (RevokeTokensRequest): Supply an access token or refresh token to have its lineage
            revoked.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | OauthError | RevokeTokensResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: RevokeTokensRequest,
) -> Error | OauthError | RevokeTokensResponse | None:
    """Revoke an access token or a refresh token.

    If you revoke a _refresh token_, be aware that:

    - The refresh token's lineage is also revoked. This means that access tokens created from that
    refresh token are also revoked.
    - The user's consent for your integration is also revoked. This means that the user must go through
    the OAuth process again to use your integration.

    Requests to this endpoint require authentication with your client ID and client secret, using _one_
    of the following methods:

    - **Basic access authentication** (Recommended): For [basic access
    authentication](https://en.wikipedia.org/wiki/Basic_access_authentication), the `{credentials}`
    string must be a Base64 encoded value of `{client id}:{client secret}`.
    - **Body parameters**: Provide your integration's credentials using the `client_id` and
    `client_secret` body parameters.

    This endpoint can't be called from a user's web-browser client because it uses client authentication
    with client secrets. Requests must come from your integration's backend, otherwise they'll be
    blocked by Canva's [Cross-Origin Resource Sharing (CORS)](https://developer.mozilla.org/en-
    US/docs/Web/HTTP/CORS) policy.

    Args:
        body (RevokeTokensRequest): Supply an access token or refresh token to have its lineage
            revoked.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | OauthError | RevokeTokensResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
