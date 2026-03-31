"""
Realtor.com site-specific property scraper.
"""

import re
from .base import BaseScraper


class RealtorScraper(BaseScraper):
    site_name = "realtor"

    async def _extract(self, page, address: str) -> dict | None:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", address).strip("-")
        url = f"https://www.realtor.com/realestateandhomes-detail/{slug}"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        beds = await self._safe_int(
            page,
            "[data-testid='property-meta-beds'] [data-testid='meta-value']",
            ".ldp-info-beds .info-val",
        )
        baths = await self._safe_text(
            page,
            "[data-testid='property-meta-baths'] [data-testid='meta-value']",
            ".ldp-info-baths .info-val",
        )
        sqft = await self._safe_int(
            page,
            "[data-testid='property-meta-sqft'] [data-testid='meta-value']",
            ".ldp-info-sqft .info-val",
        )
        year_built = await self._safe_int(
            page,
            "[data-testid='property-meta-year-built'] [data-testid='meta-value']",
            ".ldp-info-year .info-val",
        )

        return {
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "year_built": year_built,
        }
