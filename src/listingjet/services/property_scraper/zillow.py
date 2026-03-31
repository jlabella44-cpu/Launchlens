"""
Zillow site-specific property scraper.
"""

import re

from .base import BaseScraper


class ZillowScraper(BaseScraper):
    site_name = "zillow"

    async def _extract(self, page, address: str) -> dict | None:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", address).strip("-")
        url = f"https://www.zillow.com/homes/{slug}_rb/"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        beds = await self._safe_int(
            page,
            "[data-testid='bed-bath-beyond-fact']:first-child span",
            "span[data-testid='beds']",
        )
        baths = await self._safe_text(
            page,
            "[data-testid='bed-bath-beyond-fact']:nth-child(2) span",
            "span[data-testid='baths']",
        )
        sqft = await self._safe_int(
            page,
            "[data-testid='bed-bath-beyond-fact']:nth-child(3) span",
            "span[data-testid='sqft']",
        )
        year_built = await self._safe_int(
            page,
            "span[data-testid='year-built']",
            ".ds-home-fact-value:last-child",
        )
        property_type = await self._safe_text(
            page,
            "span[data-testid='home-type']",
            ".ds-home-fact-value",
        )

        if beds is None:
            return None

        return {
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "year_built": year_built,
            "property_type": property_type,
        }
