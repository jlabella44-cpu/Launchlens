"""
Base scraper class for all site-specific property scrapers.
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    site_name: str = "unknown"

    async def scrape(self, address: str) -> dict | None:
        """Launch Playwright, run extraction, return fields or None."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=random.choice(_USER_AGENTS),
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()
                await asyncio.sleep(random.uniform(1.0, 3.0))
                result = await self._extract(page, address)
                await context.close()
                await browser.close()
            return result
        except Exception as e:
            logging.getLogger(__name__).warning(
                "Scraper %s failed: %s", self.site_name, e
            )
            return None

    @abstractmethod
    async def _extract(self, page, address: str) -> dict | None: ...

    async def _safe_text(
        self, page, selector: str, fallback: str | None = None
    ) -> str | None:
        for sel in [selector, fallback]:
            if sel is None:
                continue
            try:
                el = await page.query_selector(sel)
                if el:
                    text = await el.inner_text()
                    return text.strip() if text else None
            except Exception:
                continue
        return None

    async def _safe_int(
        self, page, selector: str, fallback: str | None = None
    ) -> int | None:
        import re

        text = await self._safe_text(page, selector, fallback)
        if text:
            numbers = re.findall(r"[\d,]+", text)
            if numbers:
                return int(numbers[0].replace(",", ""))
        return None
