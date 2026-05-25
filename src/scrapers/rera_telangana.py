"""RERA Telangana project search scraper.

Portal: https://rerait.telangana.gov.in/SearchList/Search

Quirks:
- ASP.NET MVC application.
- SSL certificate issues on the search subdomain – we ignore HTTPS errors.
- Search results rendered in a paginated HTML table.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.scrapers.base import BaseScraper, _retry

log = structlog.get_logger()

URL = "https://rerait.telangana.gov.in/SearchList/Search"


class RERATelangana(BaseScraper):
    """Search RERA Telangana for registered real-estate projects."""

    @_retry
    async def scrape(
        self,
        *,
        project_name: str | None = None,
        rera_number: str | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Return a ``RERAProject``-compatible dict (or list of dicts)."""
        if not project_name and not rera_number:
            raise ValueError("Provide at least project_name or rera_number")

        async with self.get_page() as page:
            await page.goto(URL, wait_until="networkidle")
            log.info("rera_ts.loaded")

            if rera_number:
                await self._wait_and_fill(page, "#ReraNo", rera_number)
            if project_name:
                await self._wait_and_fill(page, "#ProjectName", project_name)

            await self._wait_and_click(page, "input[type='submit'], #btnSearch, button.btn-search")
            await page.wait_for_load_state("networkidle")
            log.info("rera_ts.search_submitted")

            return await self._extract_results(page)

    async def _extract_results(self, page: Any) -> dict[str, Any]:
        """Parse the results table."""
        await page.wait_for_selector("table.table, #searchResults", timeout=self.DEFAULT_TIMEOUT_MS)

        rows = await page.query_selector_all("table.table tbody tr, #searchResults tr")
        results: list[dict[str, str]] = []
        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) < 4:
                continue
            texts = [(await c.inner_text()).strip() for c in cells]
            results.append(
                {
                    "project_name": texts[0] if len(texts) > 0 else "",
                    "rera_number": texts[1] if len(texts) > 1 else "",
                    "promoter": texts[2] if len(texts) > 2 else "",
                    "status": texts[3] if len(texts) > 3 else "",
                    "registered_date": texts[4] if len(texts) > 4 else None,
                    "expiry_date": texts[5] if len(texts) > 5 else None,
                    "address": texts[6] if len(texts) > 6 else None,
                }
            )

        if len(results) == 1:
            return results[0]
        return {"results": results}
