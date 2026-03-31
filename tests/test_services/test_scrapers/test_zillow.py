import pytest
from unittest.mock import AsyncMock
from listingjet.services.property_scraper.zillow import ZillowScraper


@pytest.mark.asyncio
async def test_zillow_extracts_fields():
    scraper = ZillowScraper()
    page = AsyncMock()
    scraper._safe_int = AsyncMock(side_effect=[3, 1850, 2004])
    scraper._safe_text = AsyncMock(side_effect=["2", "Single Family"])
    result = await scraper._extract(page, "123 Oak St, Austin, TX")
    assert result is not None
    assert result["beds"] == 3


@pytest.mark.asyncio
async def test_zillow_returns_none_on_no_data():
    scraper = ZillowScraper()
    page = AsyncMock()
    scraper._safe_int = AsyncMock(return_value=None)
    scraper._safe_text = AsyncMock(return_value=None)
    result = await scraper._extract(page, "999 Nonexistent Rd")
    assert result is None
