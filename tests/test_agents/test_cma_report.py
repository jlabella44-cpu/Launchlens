"""Tests for CMAReportAgent — ensures ComparablesService output reaches the HTML."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from listingjet.agents.base import AgentContext
from listingjet.agents.cma_report import CMAReportAgent
from listingjet.models.cma_report import CMAReport
from listingjet.providers.repliers import RepliersClient
from listingjet.services.comparables import ComparablesService
from tests.test_agents.conftest import make_session_factory


def _real_comps() -> list[dict]:
    """Dict shape produced by ComparablesService (either path)."""
    return [
        {
            "address": "456 Pine St, Austin",
            "beds": 3,
            "baths": 2.0,
            "sqft": 1750,
            "price": 425_000,
            "price_per_sqft": 242.86,
            "sold_date": "2024-11-04",
            "mls_number": "C1234567",
        },
        {
            "address": "789 Maple Dr, Austin",
            "beds": 3,
            "baths": 2.5,
            "sqft": 1900,
            "price": 465_000,
            "price_per_sqft": 244.74,
            "sold_date": "2024-10-15",
            "mls_number": "C7654321",
        },
    ]


@pytest.mark.asyncio
async def test_cma_agent_uses_injected_comparables_service(db_session, listing):
    """Injected ComparablesService output flows into comparables_count + HTML + LLM prompt."""
    comps = _real_comps()

    mock_comparables = MagicMock()
    mock_comparables.fetch = AsyncMock(return_value=comps)

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Market is healthy. Price $450k–$470k.")

    mock_storage = MagicMock()
    mock_storage.upload = MagicMock()

    agent = CMAReportAgent(
        llm_provider=mock_llm,
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
        comparables_service=mock_comparables,
    )

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    # Service was called with the subject derived from the listing
    mock_comparables.fetch.assert_awaited_once()
    subject_arg = mock_comparables.fetch.call_args.args[0]
    assert "Austin" in subject_arg["address"]
    assert subject_arg["beds"] == 3

    # Comparables flowed through into the result and the DB row
    assert result["comparables_count"] == 2
    assert result["s3_key"].startswith(f"listings/{listing.id}/cma-report-")

    await db_session.flush()
    report = (await db_session.execute(
        select(CMAReport).where(CMAReport.listing_id == listing.id)
    )).scalar_one()
    assert report.comparables_count == 2
    assert report.comparables[0]["mls_number"] == "C1234567"
    assert report.comparables[1]["mls_number"] == "C7654321"

    # Storage was called with HTML containing both MLS-sourced addresses
    upload_call = mock_storage.upload.call_args
    html_bytes = upload_call.args[1]
    html = html_bytes.decode("utf-8")
    assert "456 Pine St, Austin" in html
    assert "789 Maple Dr, Austin" in html
    assert "$425,000" in html
    assert "$465,000" in html

    # LLM prompt included the real comps, not the synthetic ones
    prompt_arg = mock_llm.complete.call_args.kwargs.get("prompt") or mock_llm.complete.call_args.args[0]
    assert "456 Pine St, Austin" in prompt_arg
    assert "sold $425,000" in prompt_arg


@pytest.mark.asyncio
async def test_cma_agent_falls_back_to_service_when_no_repliers(db_session, listing):
    """When ComparablesService returns synthetic comps, the agent still produces a valid report."""
    # Use the real service but with an unconfigured Repliers client → hits synthetic path.
    real_service = ComparablesService(
        repliers_client=RepliersClient(api_key="", base_url="https://fake"),
    )

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Narrative.")

    mock_storage = MagicMock()
    mock_storage.upload = MagicMock()

    agent = CMAReportAgent(
        llm_provider=mock_llm,
        storage_service=mock_storage,
        session_factory=make_session_factory(db_session),
        comparables_service=real_service,
    )

    ctx = AgentContext(listing_id=str(listing.id), tenant_id=str(listing.tenant_id))
    result = await agent.execute(ctx)

    # Synthetic service returns TARGET_COMP_COUNT (6) comps
    assert result["comparables_count"] == 6
    mock_storage.upload.assert_called_once()
