import asyncio
import logging
from .zillow import ZillowScraper
from .redfin import RedfinScraper
from .realtor import RealtorScraper
from .homes import HomesScraper

_SCRAPERS = [ZillowScraper(), RedfinScraper(), RealtorScraper(), HomesScraper()]


async def run_all_scrapers(address: str, timeout: float = 60.0) -> dict[str, dict]:
    """Run all scrapers in parallel with global timeout. Returns {site_name: data}."""

    async def _run_one(scraper):
        result = await scraper.scrape(address)
        return scraper.site_name, result

    results = {}
    tasks = [asyncio.create_task(_run_one(s)) for s in _SCRAPERS]
    done, pending = await asyncio.wait(tasks, timeout=timeout)
    for task in pending:
        task.cancel()
    for task in done:
        if task.exception() is None:
            site_name, data = task.result()
            if data:
                results[site_name] = data
    return results
