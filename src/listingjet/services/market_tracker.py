"""
Market Tracker — automatic listing performance tracking via ATTOM Data API.

Zero agent setup required. Polls ATTOM's sale history endpoint for all
delivered listings to track MLS status, DOM, and price changes. Feeds
data into PerformanceEvent + ListingOutcome (same as IDX feed poller).

Runs as a background task in the FastAPI lifespan alongside the outbox poller.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from listingjet.config import settings
from listingjet.models.listing import Listing
from listingjet.models.performance_event import PerformanceEvent
from listingjet.services.outcome_tracker import ingest_outcome

logger = logging.getLogger(__name__)

# Poll every 6 hours — ATTOM data doesn't update in real-time
POLL_INTERVAL = 6 * 60 * 60
# Don't re-check a listing more than once per 24h
MIN_CHECK_INTERVAL = timedelta(hours=24)
BATCH_SIZE = 25
ATTOM_TIMEOUT = 15


def _build_address_string(address: dict) -> str | None:
    """Build a one-line address from listing address dict for ATTOM lookup."""
    street = address.get("street", "")
    city = address.get("city", "")
    state = address.get("state", "")
    zipcode = address.get("zip", "") or address.get("zipcode", "")
    if not street:
        return None
    parts = [street]
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    if zipcode:
        parts.append(zipcode)
    return ", ".join(parts)


async def _call_attom_sale_history(address: str) -> list[dict]:
    """Query ATTOM sale history endpoint. Returns list of sale records."""
    if not settings.attom_api_key:
        return []

    url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/salehistory"
    headers = {"apikey": settings.attom_api_key}
    params = {"address": address}

    try:
        async with httpx.AsyncClient(timeout=ATTOM_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            props = data.get("property", [])
            if not props:
                return []
            # salehistory returns sales nested under the property
            return props[0].get("saleHistory", []) or []
    except Exception:
        logger.warning("market_tracker.attom_call_failed address=%s", address[:60])
        return []


async def _call_attom_detail(address: str) -> dict | None:
    """Query ATTOM basic profile for current listing status/price."""
    if not settings.attom_api_key:
        return None

    url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/basicprofile"
    headers = {"apikey": settings.attom_api_key}
    params = {"address": address}

    try:
        async with httpx.AsyncClient(timeout=ATTOM_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            props = data.get("property", [])
            return props[0] if props else None
    except Exception:
        logger.warning("market_tracker.attom_detail_failed address=%s", address[:60])
        return None


def _translate_attom_to_idx(detail: dict | None, sale_history: list[dict]) -> dict:
    """Translate ATTOM response into the idx_data format expected by ingest_outcome."""
    result: dict = {}

    if detail:
        sale = detail.get("sale", {}) or {}
        amount = sale.get("amount", {}) or {}

        # Current listing price
        list_price = amount.get("saleamt")
        if list_price:
            result["ListPrice"] = float(list_price)

        # Sale status from ATTOM
        sale_type = str(sale.get("saletype", "")).lower()
        if sale_type in ("closed", "sold"):
            result["StandardStatus"] = "Closed"
            result["ClosePrice"] = float(list_price) if list_price else None
        elif sale_type in ("pending", "under contract"):
            result["StandardStatus"] = "Pending"
        elif sale_type in ("active", "listed"):
            result["StandardStatus"] = "Active"

        # Sale date for DOM calculation
        sale_date_str = sale.get("salerecdate") or sale.get("saletransdate")
        if sale_date_str:
            result["_sale_date"] = sale_date_str

    # Most recent sale from history (often has close price / sold price)
    if sale_history:
        latest = sale_history[0]
        amt = latest.get("amount", {}) or {}
        sold_price = amt.get("saleamt")
        if sold_price and "ClosePrice" not in result:
            result["ClosePrice"] = float(sold_price)
            result["SoldPrice"] = float(sold_price)

        sale_date = latest.get("salerecdate") or latest.get("saletransdate")
        if sale_date and "StandardStatus" not in result:
            # If there's a recent sale record, it's likely closed
            result["StandardStatus"] = "Closed"

    return result


async def _check_listing(session: AsyncSession, listing: Listing) -> bool:
    """Check a single listing against ATTOM. Returns True if data was recorded."""
    address = listing.address or {}
    address_str = _build_address_string(address)
    if not address_str:
        return False

    detail, sale_history = await asyncio.gather(
        _call_attom_detail(address_str),
        _call_attom_sale_history(address_str),
    )

    if detail is None and not sale_history:
        return False

    idx_data = _translate_attom_to_idx(detail, sale_history)
    if not idx_data:
        return False

    now = datetime.now(timezone.utc)

    # Record status change
    status_str = idx_data.get("StandardStatus", "")
    status_val = {"Active": 1.0, "Pending": 2.0, "Closed": 3.0}.get(status_str, 0.0)
    if status_val:
        session.add(PerformanceEvent(
            tenant_id=listing.tenant_id,
            listing_id=listing.id,
            signal_type="market.status_change",
            value=status_val,
            source="attom",
            recorded_at=now,
        ))

    # Record price
    list_price = idx_data.get("ListPrice")
    if list_price is not None:
        last_price_result = await session.execute(
            select(PerformanceEvent)
            .where(
                PerformanceEvent.listing_id == listing.id,
                PerformanceEvent.signal_type.in_(["market.price_change", "idx.price_change"]),
            )
            .order_by(PerformanceEvent.recorded_at.desc())
            .limit(1)
        )
        last = last_price_result.scalar_one_or_none()
        if last is None or last.value != float(list_price):
            session.add(PerformanceEvent(
                tenant_id=listing.tenant_id,
                listing_id=listing.id,
                signal_type="market.price_change",
                value=float(list_price),
                source="attom",
                recorded_at=now,
            ))

    # Ingest outcome when Pending or Closed
    if status_str in ("Pending", "Closed"):
        try:
            await ingest_outcome(
                session=session,
                listing_id=listing.id,
                tenant_id=listing.tenant_id,
                idx_data=idx_data,
                source="attom",
            )
        except Exception:
            logger.warning("market_tracker.outcome_ingest_failed listing=%s", listing.id)

    return True


class MarketTracker:
    """Background task that tracks delivered listing performance via ATTOM."""

    def __init__(self, session_factory, poll_interval: int = POLL_INTERVAL):
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False
        # Track when each listing was last checked
        self._last_checked: dict[str, datetime] = {}

    async def _process_batch(self, session: AsyncSession) -> int:
        """Find delivered listings due for checking and process them."""
        if not settings.attom_api_key:
            return 0

        now = datetime.now(timezone.utc)

        result = await session.execute(
            select(Listing).where(
                Listing.state == "delivered",
            ).limit(BATCH_SIZE * 2)  # fetch extra, filter by last-checked in memory
        )
        listings = result.scalars().all()

        checked = 0
        for listing in listings:
            lid = str(listing.id)
            last = self._last_checked.get(lid)
            if last and (now - last) < MIN_CHECK_INTERVAL:
                continue

            updated = await _check_listing(session, listing)
            self._last_checked[lid] = now
            if updated:
                checked += 1

            if checked >= BATCH_SIZE:
                break

        if checked:
            await session.flush()
            logger.info("market_tracker.batch_complete checked=%d", checked)

        return checked

    async def run(self):
        """Long-running poll loop. Call from FastAPI lifespan."""
        if not settings.attom_api_key:
            logger.info("market_tracker.disabled — no ATTOM_API_KEY configured")
            return

        self._running = True
        logger.info("market_tracker.started poll_interval=%ds", self._poll_interval)

        while self._running:
            try:
                async with self._session_factory() as session:
                    async with session.begin():
                        await self._process_batch(session)
            except Exception:
                logger.exception("market_tracker.error")
            await asyncio.sleep(self._poll_interval)

    def stop(self):
        self._running = False
