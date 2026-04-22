#!/usr/bin/env python3
"""Local end-to-end pipeline smoke test against docker-compose.

Runs the 16-step pre-launch checklist documented in the pre-launch plan
against the compose stack (postgres, redis, temporal, api, worker,
optionally LocalStack + mailpit + httpbin).

Usage:
    # Start the stack
    docker-compose up -d
    # Wait for api health
    until curl -sf http://localhost:8000/health; do sleep 2; done
    # Run the smoke
    python scripts/e2e_local.py
    # Or with a different base URL
    E2E_BASE_URL=http://localhost:8000 python scripts/e2e_local.py

Exit codes:
    0 = all automatable steps passed; manual steps are announced but
        not gated
    1 = an automatable step failed

Flags:
    --real-providers   Set USE_MOCK_PROVIDERS=false in the environment
                       before running (requires real API keys for the
                       AI providers — costs a few dollars per run).
    --quick            Skip the long pipeline-processing wait (steps
                       6-10); useful for CI where you just want to
                       verify the API contract.
"""
import argparse
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(30.0, connect=5.0)
PIPELINE_WAIT_SECONDS = 300  # 5 min hard cap on AWAITING_REVIEW
DELIVERED_WAIT_SECONDS = 240  # 4 min hard cap on DELIVERED


@dataclass
class StepResult:
    name: str
    passed: bool
    detail: str = ""
    manual: bool = False
    skipped: bool = False


@dataclass
class State:
    token: str = ""
    tenant_id: str = ""
    user_email: str = ""
    listing_id: str = ""
    demo_id: str = ""
    results: list[StepResult] = field(default_factory=list)


def _log(state: State, name: str, passed: bool, detail: str = "", manual: bool = False, skipped: bool = False) -> None:
    marker = "SKIP" if skipped else ("MANUAL" if manual else ("PASS" if passed else "FAIL"))
    print(f"[{marker}] {name}: {detail}")
    state.results.append(StepResult(name, passed, detail, manual, skipped))


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---- Steps ---------------------------------------------------------------


def step_1_register(client: httpx.Client, state: State) -> None:
    state.user_email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/v1/auth/register", json={
        "email": state.user_email,
        "password": "E2ePass1!ValidLong",
        "name": "E2E Tester",
        "company_name": "E2E Smoke LLC",
        "plan_tier": "free",
        "consent": True,
        "ai_consent": True,
    })
    if resp.status_code not in (200, 201):
        _log(state, "1. register", False, f"{resp.status_code} {resp.text[:200]}")
        return
    payload = resp.json()
    state.token = payload["access_token"]
    # Decode tenant_id from the token without verifying — sub/tenant_id are non-secret
    import base64, json as _json
    parts = state.token.split(".")
    body = _json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    state.tenant_id = body["tenant_id"]
    _log(state, "1. register", True, f"tenant={state.tenant_id[:8]}... email={state.user_email}")


def step_2_welcome_email(state: State) -> None:
    _log(state, "2. welcome email", True,
         "check SMTP capture (mailpit http://localhost:8025) or verify manually",
         manual=True)


def step_3_create_listing(client: httpx.Client, state: State) -> None:
    resp = client.post("/v1/listings", json={
        "address": {"street": "123 Smoke St", "city": "Testville", "state": "CA", "zip": "94000"},
        "metadata": {"beds": 3, "baths": 2},
    }, headers=_auth(state.token))
    if resp.status_code not in (200, 201):
        _log(state, "3. create listing", False, f"{resp.status_code} {resp.text[:200]}")
        return
    state.listing_id = resp.json()["id"]
    _log(state, "3. create listing", True, f"listing={state.listing_id[:8]}...")


def step_4_upload_urls(client: httpx.Client, state: State) -> None:
    if not state.listing_id:
        _log(state, "4. upload-urls", False, "skipped — no listing_id", skipped=True)
        return
    resp = client.post(
        f"/v1/listings/{state.listing_id}/upload-urls",
        json={"filenames": ["kitchen.jpg", "living.jpg", "master.jpg"]},
        headers=_auth(state.token),
    )
    if resp.status_code != 200:
        _log(state, "4. upload-urls", False, f"{resp.status_code} {resp.text[:200]}")
        return
    urls = resp.json().get("upload_urls", [])
    _log(state, "4. upload-urls", True, f"got {len(urls)} presigned URLs")


def step_5_register_assets(client: httpx.Client, state: State) -> None:
    if not state.listing_id:
        _log(state, "5. register assets", False, "skipped — no listing_id", skipped=True)
        return
    assets = [
        {"file_path": f"s3://mock/listings/{state.listing_id}/{n}.jpg",
         "file_hash": f"h{n:03d}deadbeef"}
        for n in range(3)
    ]
    resp = client.post(
        f"/v1/listings/{state.listing_id}/assets",
        json={"assets": assets},
        headers=_auth(state.token),
    )
    if resp.status_code not in (200, 201):
        _log(state, "5. register assets", False, f"{resp.status_code} {resp.text[:200]}")
        return
    _log(state, "5. register assets", True, f"registered {len(assets)} assets, pipeline triggered")


def step_6_7_wait_awaiting_review(client: httpx.Client, state: State, quick: bool) -> None:
    if quick:
        _log(state, "6-7. wait AWAITING_REVIEW", True, "skipped via --quick", skipped=True)
        return
    if not state.listing_id:
        _log(state, "6-7. wait AWAITING_REVIEW", False, "no listing_id", skipped=True)
        return
    deadline = time.time() + PIPELINE_WAIT_SECONDS
    last_state = None
    while time.time() < deadline:
        resp = client.get(f"/v1/listings/{state.listing_id}", headers=_auth(state.token))
        if resp.status_code == 200:
            last_state = resp.json().get("state")
            if last_state == "awaiting_review":
                _log(state, "6-7. wait AWAITING_REVIEW", True, f"reached in {PIPELINE_WAIT_SECONDS - int(deadline - time.time())}s")
                return
            if last_state in ("failed", "cancelled"):
                _log(state, "6-7. wait AWAITING_REVIEW", False, f"terminal state: {last_state}")
                return
        time.sleep(5)
    _log(state, "6-7. wait AWAITING_REVIEW", False, f"timed out at state={last_state}")


def step_8_approve(client: httpx.Client, state: State, quick: bool) -> None:
    if quick:
        _log(state, "8. approve", True, "skipped via --quick", skipped=True)
        return
    if not state.listing_id:
        _log(state, "8. approve", False, "no listing_id", skipped=True)
        return
    resp = client.post(f"/v1/listings/{state.listing_id}/approve", headers=_auth(state.token))
    if resp.status_code not in (200, 202):
        _log(state, "8. approve", False, f"{resp.status_code} {resp.text[:200]}")
        return
    _log(state, "8. approve", True, "phase 2 started")


def step_9_10_wait_delivered(client: httpx.Client, state: State, quick: bool) -> None:
    if quick:
        _log(state, "9-10. wait DELIVERED", True, "skipped via --quick", skipped=True)
        return
    if not state.listing_id:
        _log(state, "9-10. wait DELIVERED", False, "no listing_id", skipped=True)
        return
    deadline = time.time() + DELIVERED_WAIT_SECONDS
    last_state = None
    while time.time() < deadline:
        resp = client.get(f"/v1/listings/{state.listing_id}", headers=_auth(state.token))
        if resp.status_code == 200:
            last_state = resp.json().get("state")
            if last_state == "delivered":
                _log(state, "9-10. wait DELIVERED", True, "pipeline complete")
                return
            if last_state in ("failed", "cancelled"):
                _log(state, "9-10. wait DELIVERED", False, f"terminal state: {last_state}")
                return
        time.sleep(5)
    _log(state, "9-10. wait DELIVERED", False, f"timed out at state={last_state}")


def step_11_export(client: httpx.Client, state: State, quick: bool) -> None:
    if quick:
        _log(state, "11. export MLS bundle", True, "skipped via --quick", skipped=True)
        return
    if not state.listing_id:
        _log(state, "11. export MLS bundle", False, "no listing_id", skipped=True)
        return
    resp = client.get(f"/v1/listings/{state.listing_id}/export?mode=mls", headers=_auth(state.token))
    if resp.status_code != 200:
        _log(state, "11. export MLS bundle", False, f"{resp.status_code} {resp.text[:200]}")
        return
    _log(state, "11. export MLS bundle", True, "presigned URL returned")


def step_12_webhook(state: State) -> None:
    _log(state, "12. webhook delivery", True,
         "set tenant webhook_url via PATCH /v1/settings then watch httpbin/webhook.site",
         manual=True)


def step_13_pipeline_email(state: State) -> None:
    _log(state, "13. pipeline-complete email", True,
         "check mailpit or real inbox",
         manual=True)


def step_14_retry(state: State) -> None:
    _log(state, "14. worker-kill retry", True,
         "kill worker container mid-pipeline, POST /v1/listings/{id}/retry",
         manual=True)


def step_15_cancel(client: httpx.Client, state: State) -> None:
    # Create a fresh listing so we don't disturb the one that reached DELIVERED
    resp = client.post("/v1/listings", json={
        "address": {"street": "1 Cancel Way"}, "metadata": {},
    }, headers=_auth(state.token))
    if resp.status_code not in (200, 201):
        _log(state, "15. cancel", False, f"create: {resp.status_code}")
        return
    cancel_id = resp.json()["id"]
    resp = client.post(f"/v1/listings/{cancel_id}/cancel", headers=_auth(state.token))
    if resp.status_code not in (200, 202):
        _log(state, "15. cancel", False, f"{resp.status_code} {resp.text[:200]}")
        return
    body = resp.json()
    ok = body.get("state") in ("cancelled", "CANCELLED")
    _log(state, "15. cancel", ok, f"state={body.get('state')}")


def step_16_demo(client: httpx.Client, state: State) -> None:
    # Demo upload is unauthenticated; creates a demo listing without a tenant
    resp = client.post("/v1/demo/upload", json={
        "address": {"street": "1 Demo Rd"},
        "assets": [{"file_path": "s3://mock/demo/sample.jpg", "file_hash": "demoh001"}],
    })
    if resp.status_code not in (200, 201):
        _log(state, "16. demo upload", False, f"{resp.status_code} {resp.text[:200]}")
        return
    state.demo_id = resp.json().get("id", "")
    _log(state, "16. demo upload", True, f"demo={state.demo_id[:8]}...")


# ---- Main ----------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--real-providers", action="store_true",
                        help="Run with real AI providers (costs money).")
    parser.add_argument("--quick", action="store_true",
                        help="Skip pipeline-processing wait steps.")
    args = parser.parse_args()

    if args.real_providers:
        os.environ["USE_MOCK_PROVIDERS"] = "false"
        print("! real-providers mode — AI calls will cost real money")

    state = State()

    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        # Pre-flight
        try:
            r = client.get("/health")
            if r.status_code != 200:
                print(f"! /health returned {r.status_code} — is the API running?")
                return 1
        except httpx.ConnectError as e:
            print(f"! cannot reach {BASE_URL}: {e}")
            print("  Start the stack: docker-compose up -d")
            return 1

        step_1_register(client, state)
        step_2_welcome_email(state)
        step_3_create_listing(client, state)
        step_4_upload_urls(client, state)
        step_5_register_assets(client, state)
        step_6_7_wait_awaiting_review(client, state, args.quick)
        step_8_approve(client, state, args.quick)
        step_9_10_wait_delivered(client, state, args.quick)
        step_11_export(client, state, args.quick)
        step_12_webhook(state)
        step_13_pipeline_email(state)
        step_14_retry(state)
        step_15_cancel(client, state)
        step_16_demo(client, state)

    # Summary
    passed = sum(1 for r in state.results if r.passed and not r.manual and not r.skipped)
    failed = sum(1 for r in state.results if not r.passed and not r.skipped)
    manual = sum(1 for r in state.results if r.manual)
    skipped = sum(1 for r in state.results if r.skipped)
    print()
    print(f"Auto-passed: {passed}  Auto-failed: {failed}  Manual-check: {manual}  Skipped: {skipped}")
    if failed:
        print("\nFailures:")
        for r in state.results:
            if not r.passed and not r.skipped:
                print(f"  - {r.name}: {r.detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
