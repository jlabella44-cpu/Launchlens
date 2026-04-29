"""Unit tests for TemporalClient.start_pipeline.

Pinning the id_reuse_policy guards the retry-pipeline path: if it ever silently
flips back to REJECT_DUPLICATE, retries on stuck listings will no-op and the
"Stalled" UI will be unfixable from the front-end.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from temporalio.common import WorkflowIDReusePolicy

from listingjet.temporal_client import TemporalClient


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
