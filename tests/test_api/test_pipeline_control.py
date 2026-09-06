import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from listingjet.models.listing import Listing, ListingState
from listingjet.models.pipeline_job import JobStatus, PipelineJob


async def _register(client: AsyncClient) -> tuple[str, str]:
    import jwt as pyjwt

    from listingjet.config import settings
    email = f"test-{uuid.uuid4()}@example.com"
    resp = await client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "T", "company_name": "PipeCo", "plan_tier": "free",
    })
    token = resp.json()["access_token"]
    return token, pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["tenant_id"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.mark.asyncio
async def test_registering_assets_enqueues_pipeline_jobs(async_client, db_session):
    from listingjet.models.tenant import Tenant
    token, tenant_id = await _register(async_client)
    # Credit-billed tenants (the register default) start listings in DRAFT, where
    # asset registration doesn't auto-start the pipeline (see test_assets.py).
    # Flip to legacy billing so the new listing starts NEW -> UPLOADING on assets.
    tenant = await db_session.get(Tenant, uuid.UUID(tenant_id))
    tenant.billing_model = "legacy"
    await db_session.commit()
    lid = (await async_client.post("/listings", json={"address": {"street": "1 Q St"}, "metadata": {}},
                                   headers=_auth(token))).json()["id"]
    resp = await async_client.post(f"/listings/{lid}/assets", json={"assets": [
        {"file_path": f"listings/{lid}/uploads/a.jpg", "file_hash": "h1"},
    ]}, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    jobs = (await db_session.execute(select(PipelineJob).where(PipelineJob.listing_id == uuid.UUID(lid)))).scalars().all()
    assert {j.step for j in jobs} >= {"ingestion", "packaging", "await_review", "distribution"}
    assert next(j for j in jobs if j.step == "await_review").status == JobStatus.WAITING


@pytest.mark.asyncio
async def test_pipeline_status_reads_jobs(async_client, db_session):
    from listingjet.models.tenant import Tenant
    token, tenant_id = await _register(async_client)
    tenant = await db_session.get(Tenant, uuid.UUID(tenant_id))
    tenant.billing_model = "legacy"
    await db_session.commit()
    lid = (await async_client.post("/listings", json={"address": {"street": "2 Q St"}, "metadata": {}},
                                   headers=_auth(token))).json()["id"]
    await async_client.post(f"/listings/{lid}/assets", json={"assets": [
        {"file_path": f"listings/{lid}/uploads/a.jpg", "file_hash": "h2"}]}, headers=_auth(token))
    resp = await async_client.get(f"/listings/{lid}/pipeline-status", headers=_auth(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["listing_id"] == lid
    names = [s["name"] for s in body["steps"]]
    assert names[0] == "ingestion" and "await_review" in names
    assert body["steps"][0]["status"] == "pending" and body["steps"][0]["error"] is None


@pytest.mark.asyncio
async def test_approve_completes_review_gate(async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = Listing(tenant_id=uuid.UUID(tenant_id), address={"street": "3 Q St"}, metadata_={},
                      state=ListingState.IN_REVIEW)
    db_session.add(listing)
    await db_session.flush()
    db_session.add(PipelineJob(tenant_id=listing.tenant_id, listing_id=listing.id, step="await_review",
                               status=JobStatus.WAITING))
    await db_session.flush()
    await db_session.commit()
    resp = await async_client.post(f"/listings/{listing.id}/approve", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    job = (await db_session.execute(select(PipelineJob).where(
        PipelineJob.listing_id == listing.id, PipelineJob.step == "await_review"))).scalar_one()
    assert job.status == JobStatus.DONE


@pytest.mark.asyncio
async def test_retry_requeues_failed_listing(async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = Listing(tenant_id=uuid.UUID(tenant_id), address={"street": "4 Q St"}, metadata_={},
                      state=ListingState.FAILED)
    db_session.add(listing)
    await db_session.flush()
    db_session.add(PipelineJob(tenant_id=listing.tenant_id, listing_id=listing.id, step="ingestion",
                               status=JobStatus.FAILED, attempts=3, error="boom"))
    await db_session.flush()
    await db_session.commit()
    resp = await async_client.post(f"/listings/{listing.id}/retry", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["state"] == "uploading"
    job = (await db_session.execute(select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalar_one()
    assert job.status == JobStatus.QUEUED and job.attempts == 0 and job.error is None


@pytest.mark.asyncio
async def test_cancel_cancels_jobs(async_client, db_session):
    token, tenant_id = await _register(async_client)
    listing = Listing(tenant_id=uuid.UUID(tenant_id), address={"street": "5 Q St"}, metadata_={},
                      state=ListingState.UPLOADING)
    db_session.add(listing)
    await db_session.flush()
    db_session.add(PipelineJob(tenant_id=listing.tenant_id, listing_id=listing.id, step="ingestion"))
    await db_session.flush()
    await db_session.commit()
    resp = await async_client.post(f"/listings/{listing.id}/cancel", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    job = (await db_session.execute(select(PipelineJob).where(PipelineJob.listing_id == listing.id))).scalar_one()
    assert job.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_deep_health_reports_worker_not_temporal(async_client):
    resp = await async_client.get("/health/deep")
    data = resp.json()
    assert "temporal" not in data
    assert "worker" in data
