from unittest.mock import patch

import pytest
from fastapi import HTTPException

from listingjet import features
from listingjet.pipeline.definition import STEP_INDEX


def test_flag_names_are_exact():
    assert features.FLAG_NAMES == frozenset({
        "learning", "health_score", "performance_intelligence", "help_agent",
        "microsite", "webhooks", "listing_permissions",
    })


def test_enabled_reads_settings_each_call():
    with patch.object(features.settings, "features", ""):
        assert features.enabled("microsite") is False
    with patch.object(features.settings, "features", "microsite, webhooks"):
        assert features.enabled("microsite") is True
        assert features.enabled("webhooks") is True
        assert features.enabled("learning") is False


def test_enabled_rejects_unknown_name():
    with pytest.raises(ValueError, match="unknown feature"):
        features.enabled("nope")


@pytest.mark.asyncio
async def test_require_feature_dependency():
    dep = features.require_feature("help_agent")
    with patch.object(features.settings, "features", ""):
        with pytest.raises(HTTPException) as exc:
            await dep()
        assert exc.value.status_code == 404
    with patch.object(features.settings, "features", "help_agent"):
        assert await dep() is None


def test_deferred_steps_carry_feature_gates():
    assert STEP_INDEX["learning"].gate == "feature:learning"
    assert STEP_INDEX["health_score"].gate == "feature:health_score"
    assert STEP_INDEX["performance_intelligence"].gate == "feature:performance_intelligence"
    assert STEP_INDEX["microsite"].gate == "feature:microsite"


@pytest.mark.asyncio
async def test_settings_features_endpoint(async_client):
    import uuid
    email = f"t-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "T", "company_name": "FlagCo", "plan_tier": "free",
    })
    token = reg.json()["access_token"]
    with patch.object(features.settings, "features", "microsite,learning"):
        resp = await async_client.get("/settings/features", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"features": ["learning", "microsite"]}


@pytest.mark.asyncio
async def test_flagged_router_absent_when_off(async_client):
    # help_agent router is registered at app-build time when FEATURES includes
    # it (see tests/conftest.py), but api/help_agent.py also attaches a
    # require_feature("help_agent") dependency to the router itself, so the
    # runtime check must hold even though the route exists.
    import uuid
    email = f"t-{uuid.uuid4()}@example.com"
    reg = await async_client.post("/auth/register", json={
        "email": email, "password": "TestPass1!", "name": "T", "company_name": "FlagCo", "plan_tier": "free",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(features.settings, "features", ""):
        resp = await async_client.get("/help/history?session_id=x", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Feature not enabled"

    with patch.object(features.settings, "features", "help_agent"):
        resp = await async_client.get("/help/history?session_id=x", headers=headers)
    assert resp.status_code != 404
