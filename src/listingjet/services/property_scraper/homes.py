"""
Homes.com site-specific property scraper.
"""

from urllib.parse import quote_plus

from .base import BaseScraper


class HomesScraper(BaseScraper):
    site_name = "homes"

    async def _extract(self, page, address: str) -> dict | None:
        encoded = quote_plus(address)
        url = f"https://www.homes.com/property-search/{encoded}/"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        try:
            await page.click(".property-card a", timeout=5000)
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass

        beds = await self._safe_int(
            page,
            "[data-testid='beds-value']",
            ".property-info-beds .value",
        )
        baths = await self._safe_text(
            page,
            "[data-testid='baths-value']",
            ".property-info-baths .value",
        )
        sqft = await self._safe_int(
            page,
            "[data-testid='sqft-value']",
            ".property-info-sqft .value",
        )
        year_built = await self._safe_int(
            page,
            "[data-testid='year-built-value']",
            ".property-info-year .value",
        )

        return {
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "year_built": year_built,
        }
