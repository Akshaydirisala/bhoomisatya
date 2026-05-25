"""RERA Andhra Pradesh project search scraper.

Portal: https://rera.ap.gov.in/Reports/ApprovedProjectSearch.aspx

Quirks:
- ASP.NET WebForms – every POST requires __VIEWSTATE, __VIEWSTATEGENERATOR,
  and __EVENTVALIDATION tokens extracted from hidden form fields.
- Has a unique promoter GRADING system (A+, A, B, C, etc.).
- ViewState can be very large (>100 KB); we extract it just before each POST.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.scrapers.base import BaseScraper, _retry

log = structlog.get_logger()

URL = "https://rera.ap.gov.in/Reports/ApprovedProjectSearch.aspx"


class RERAAP(BaseScraper):
    """Search RERA AP for approved real-estate projects with promoter grades."""

    @_retry
    async def scrape(
        self,
        *,
        project_name: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Return a ``RERAProject``-compatible dict (with extra ``grade`` field)."""
        async with self.get_page() as page:
            await page.goto(URL, wait_until="networkidle")
            log.info("rera_ap.loaded")

            # Extract ASP.NET hidden tokens (needed for postback)
            viewstate = await self._hidden_value(page, "#__VIEWSTATE")
            viewstate_gen = await self._hidden_value(page, "#__VIEWSTATEGENERATOR")
            event_val = await self._hidden_value(page, "#__EVENTVALIDATION")
            log.debug(
                "rera_ap.tokens",
                vs_len=len(viewstate or ""),
                vsg=viewstate_gen,
            )

            # Fill search and submit
            await self._wait_and_fill(
                page, "#txtProjectName, #ContentPlaceHolder1_txtProjectName", project_name
            )
            await self._wait_and_click(page, "#btnSearch, #ContentPlaceHolder1_btnSearch")
            await page.wait_for_load_state("networkidle")
            log.info("rera_ap.search_submitted")

            return await self._extract_results(page)

    async def _hidden_value(self, page: Any, selector: str) -> str | None:
        el = await page.query_selector(selector)
        if el:
            return await el.get_attribute("value")
        return None

    async def _extract_results(self, page: Any) -> dict[str, Any]:
        await page.wait_for_selector(
            "#GridView1, #ContentPlaceHolder1_GridView1, table.table",
            timeout=self.DEFAULT_TIMEOUT_MS,
        )

        rows = await page.query_selector_all("#GridView1 tr, #ContentPlaceHolder1_GridView1 tr")
        results: list[dict[str, Any]] = []
        for row in rows[1:]:  # skip header
            cells = await row.query_selector_all("td")
            if len(cells) < 4:
                continue
            texts = [(await c.inner_text()).strip() for c in cells]
            results.append(
                {
                    "project_name": texts[0] if len(texts) > 0 else "",
                    "rera_number": texts[1] if len(texts) > 1 else "",
                    "promoter": texts[2] if len(texts) > 2 else "",
                    "grade": texts[3] if len(texts) > 3 else None,
                    "status": texts[4] if len(texts) > 4 else "",
                    "registered_date": texts[5] if len(texts) > 5 else None,
                    "expiry_date": texts[6] if len(texts) > 6 else None,
                }
            )

        if len(results) == 1:
            return results[0]
        return {"results": results}
