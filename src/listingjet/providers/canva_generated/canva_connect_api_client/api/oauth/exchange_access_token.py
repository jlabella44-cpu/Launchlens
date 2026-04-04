from http import HTTPStatus
from typing import Any

import httpx

from ...client import AuthenticatedClient, Client
from ...models.error import Error
from ...models.exchange_access_token_response import ExchangeAccessTokenResponse
from ...models.exchange_auth_code_request import ExchangeAuthCodeRequest
from ...models.exchange_refresh_token_request import ExchangeRefreshTokenRequest
from ...models.oauth_error import OauthError
from ...types import Response


def _get_kwargs(
    *,
    body: ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/oauth/token",
    }

    _kwargs["data"] = body.to_dict()

    headers["Content-Type"] = "application/x-www-form-urlencoded"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Error | ExchangeAccessTokenResponse | OauthError:
    if response.status_code == 200:
        response_200 = ExchangeAccessTokenResponse.from_dict(response.json())

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
) -> Response[Error | ExchangeAccessTokenResponse | OauthError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest,
) -> Response[Error | ExchangeAccessTokenResponse | OauthError]:
    """This endpoint implements the OAuth 2.0 `token` endpoint, as part of the Authorization Code flow with
    Proof Key for Code Exchange (PKCE). For more information, see
    [Authentication](https://www.canva.dev/docs/connect/authentication/).

    To generate an access token, you must provide one of the following:

    - An authorization code
    - A refresh token

    Generating a token using either an authorization code or a refresh token allows your integration to
    act on behalf of a user. You must first [obtain user authorization and get an authorization
    code](https://www.canva.dev/docs/connect/authentication/#obtain-user-authorization).

    Access tokens may be up to 4 KB in size, and are only valid for a specified period of time. The
    expiry time (currently 4 hours) is shown in the endpoint response and is subject to change.

    **Endpoint authentication**

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

    **Generate an access token using an authorization code**

    To generate an access token with an authorization code, you must:

    - Set `grant_type` to `authorization_code`.
    - Provide the `code_verifier` value that you generated when creating the user authorization URL.
    - Provide the authorization code you received after the user authorized the integration.

    **Generate an access token using a refresh token**

    Using the `refresh_token` value from a previous user token request, you can get a new access token
    with the same or smaller scope as the previous one, but with a refreshed expiry time. You will also
    receive a new refresh token that you can use to refresh the access token again.

    To refresh an existing access token, you must:

    - Set `grant_type` to `refresh_token`.
    - Provide the `refresh_token` from a previous token request.

    Args:
        body (ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ExchangeAccessTokenResponse | OauthError]
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
    body: ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest,
) -> Error | ExchangeAccessTokenResponse | OauthError | None:
    """This endpoint implements the OAuth 2.0 `token` endpoint, as part of the Authorization Code flow with
    Proof Key for Code Exchange (PKCE). For more information, see
    [Authentication](https://www.canva.dev/docs/connect/authentication/).

    To generate an access token, you must provide one of the following:

    - An authorization code
    - A refresh token

    Generating a token using either an authorization code or a refresh token allows your integration to
    act on behalf of a user. You must first [obtain user authorization and get an authorization
    code](https://www.canva.dev/docs/connect/authentication/#obtain-user-authorization).

    Access tokens may be up to 4 KB in size, and are only valid for a specified period of time. The
    expiry time (currently 4 hours) is shown in the endpoint response and is subject to change.

    **Endpoint authentication**

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

    **Generate an access token using an authorization code**

    To generate an access token with an authorization code, you must:

    - Set `grant_type` to `authorization_code`.
    - Provide the `code_verifier` value that you generated when creating the user authorization URL.
    - Provide the authorization code you received after the user authorized the integration.

    **Generate an access token using a refresh token**

    Using the `refresh_token` value from a previous user token request, you can get a new access token
    with the same or smaller scope as the previous one, but with a refreshed expiry time. You will also
    receive a new refresh token that you can use to refresh the access token again.

    To refresh an existing access token, you must:

    - Set `grant_type` to `refresh_token`.
    - Provide the `refresh_token` from a previous token request.

    Args:
        body (ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ExchangeAccessTokenResponse | OauthError
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest,
) -> Response[Error | ExchangeAccessTokenResponse | OauthError]:
    """This endpoint implements the OAuth 2.0 `token` endpoint, as part of the Authorization Code flow with
    Proof Key for Code Exchange (PKCE). For more information, see
    [Authentication](https://www.canva.dev/docs/connect/authentication/).

    To generate an access token, you must provide one of the following:

    - An authorization code
    - A refresh token

    Generating a token using either an authorization code or a refresh token allows your integration to
    act on behalf of a user. You must first [obtain user authorization and get an authorization
    code](https://www.canva.dev/docs/connect/authentication/#obtain-user-authorization).

    Access tokens may be up to 4 KB in size, and are only valid for a specified period of time. The
    expiry time (currently 4 hours) is shown in the endpoint response and is subject to change.

    **Endpoint authentication**

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

    **Generate an access token using an authorization code**

    To generate an access token with an authorization code, you must:

    - Set `grant_type` to `authorization_code`.
    - Provide the `code_verifier` value that you generated when creating the user authorization URL.
    - Provide the authorization code you received after the user authorized the integration.

    **Generate an access token using a refresh token**

    Using the `refresh_token` value from a previous user token request, you can get a new access token
    with the same or smaller scope as the previous one, but with a refreshed expiry time. You will also
    receive a new refresh token that you can use to refresh the access token again.

    To refresh an existing access token, you must:

    - Set `grant_type` to `refresh_token`.
    - Provide the `refresh_token` from a previous token request.

    Args:
        body (ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ExchangeAccessTokenResponse | OauthError]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest,
) -> Error | ExchangeAccessTokenResponse | OauthError | None:
    """This endpoint implements the OAuth 2.0 `token` endpoint, as part of the Authorization Code flow with
    Proof Key for Code Exchange (PKCE). For more information, see
    [Authentication](https://www.canva.dev/docs/connect/authentication/).

    To generate an access token, you must provide one of the following:

    - An authorization code
    - A refresh token

    Generating a token using either an authorization code or a refresh token allows your integration to
    act on behalf of a user. You must first [obtain user authorization and get an authorization
    code](https://www.canva.dev/docs/connect/authentication/#obtain-user-authorization).

    Access tokens may be up to 4 KB in size, and are only valid for a specified period of time. The
    expiry time (currently 4 hours) is shown in the endpoint response and is subject to change.

    **Endpoint authentication**

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

    **Generate an access token using an authorization code**

    To generate an access token with an authorization code, you must:

    - Set `grant_type` to `authorization_code`.
    - Provide the `code_verifier` value that you generated when creating the user authorization URL.
    - Provide the authorization code you received after the user authorized the integration.

    **Generate an access token using a refresh token**

    Using the `refresh_token` value from a previous user token request, you can get a new access token
    with the same or smaller scope as the previous one, but with a refreshed expiry time. You will also
    receive a new refresh token that you can use to refresh the access token again.

    To refresh an existing access token, you must:

    - Set `grant_type` to `refresh_token`.
    - Provide the `refresh_token` from a previous token request.

    Args:
        body (ExchangeAuthCodeRequest | ExchangeRefreshTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ExchangeAccessTokenResponse | OauthError
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
