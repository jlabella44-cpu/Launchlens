"""Unit tests for TemporalClient.start_pipeline.

Pinning the id_reuse_policy guards the retry-pipeline path: if it ever silently
flips back to REJECT_DUPLICATE, retries on stuck listings will no-op and the
"Stalled" UI will be unfixable from the front-end.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio.common import WorkflowIDReusePolicy

from listingjet.temporal_client import TemporalClient, connect_temporal


def _make_client_mock() -> MagicMock:
    """Build an awaitable Client mock whose start_workflow records its kwargs."""
    fake_handle = MagicMock()
    fake_handle.id = "listing-pipeline-abc"
    client = MagicMock()
    client.start_workflow = AsyncMock(return_value=fake_handle)
    return client


@pytest.mark.asyncio
async def test_start_pipeline_default_uses_reject_duplicate():
    tc = TemporalClient()
    client = _make_client_mock()
    with patch.object(tc, "_connect", AsyncMock(return_value=client)):
        await tc.start_pipeline(listing_id="abc", tenant_id="t1")
    kwargs = client.start_workflow.await_args.kwargs
    assert kwargs["id_reuse_policy"] == WorkflowIDReusePolicy.REJECT_DUPLICATE
    assert kwargs["id"] == "listing-pipeline-abc"


@pytest.mark.asyncio
async def test_start_pipeline_retry_uses_terminate_if_running():
    """terminate_existing=True must pick TERMINATE_IF_RUNNING — the whole
    point of this flag is to free a stuck workflow ID so retries actually run."""
    tc = TemporalClient()
    client = _make_client_mock()
    with patch.object(tc, "_connect", AsyncMock(return_value=client)):
        await tc.start_pipeline(listing_id="abc", tenant_id="t1", terminate_existing=True)
    kwargs = client.start_workflow.await_args.kwargs
    assert kwargs["id_reuse_policy"] == WorkflowIDReusePolicy.TERMINATE_IF_RUNNING


@pytest.mark.asyncio
async def test_connect_temporal_local_no_tls_no_api_key():
    """Self-hosted/local: no API key, no TLS — bare namespaced connect."""
    with patch("listingjet.temporal_client.settings") as s, \
         patch("listingjet.temporal_client.Client.connect", AsyncMock()) as conn:
        s.temporal_host = "localhost:7233"
        s.temporal_namespace = "default"
        s.temporal_api_key = ""
        s.temporal_tls = False
        await connect_temporal()
    args, kwargs = conn.await_args
    assert args == ("localhost:7233",)
    assert kwargs == {"namespace": "default"}


@pytest.mark.asyncio
async def test_connect_temporal_cloud_api_key_implies_tls():
    """Temporal Cloud: setting an API key must auto-enable TLS."""
    with patch("listingjet.temporal_client.settings") as s, \
         patch("listingjet.temporal_client.Client.connect", AsyncMock()) as conn:
        s.temporal_host = "ns.acct.tmprl.cloud:7233"
        s.temporal_namespace = "ns.acct"
        s.temporal_api_key = "tk_secret"
        s.temporal_tls = False
        await connect_temporal()
    kwargs = conn.await_args.kwargs
    assert kwargs["api_key"] == "tk_secret"
    assert kwargs["tls"] is True
    assert kwargs["namespace"] == "ns.acct"


@pytest.mark.asyncio
async def test_connect_temporal_passes_overrides():
    """Callers (the worker) pass interceptors without re-stating auth."""
    sentinel = [object()]
    with patch("listingjet.temporal_client.settings") as s, \
         patch("listingjet.temporal_client.Client.connect", AsyncMock()) as conn:
        s.temporal_host = "localhost:7233"
        s.temporal_namespace = "default"
        s.temporal_api_key = ""
        s.temporal_tls = False
        await connect_temporal(interceptors=sentinel)
    assert conn.await_args.kwargs["interceptors"] is sentinel
