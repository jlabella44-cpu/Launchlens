"""
Redfin site-specific property scraper.
"""

from urllib.parse import quote_plus
from .base import BaseScraper


class RedfinScraper(BaseScraper):
    site_name = "redfin"

    async def _extract(self, page, address: str) -> dict | None:
        encoded = quote_plus(address)
        url = f"https://www.redfin.com/search?q={encoded}"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        try:
            await page.click(".HomeCard a", timeout=5000)
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        beds = await self._safe_int(
            page,
            "[data-rf-test-id='abp-beds'] .statsValue",
            ".beds-baths-sqft .value:first-child",
        )
        baths = await self._safe_text(
            page,
            "[data-rf-test-id='abp-baths'] .statsValue",
            ".beds-baths-sqft .value:nth-child(2)",
        )
        sqft = await self._safe_int(
            page,
            "[data-rf-test-id='abp-sqFt'] .statsValue",
            ".beds-baths-sqft .value:nth-child(3)",
        )
        year_built = await self._safe_int(
            page,
            ".keyDetailsList [data-rf-test-id='abp-yearBuilt'] .entryItemContent",
            ".yr-built .value",
        )

        return {
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "year_built": year_built,
        }
