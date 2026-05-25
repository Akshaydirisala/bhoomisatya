"""MeeBhoomi (Andhra Pradesh) land records scraper.

Portal: https://meebhoomi.ap.gov.in

Quirks:
- Similar cascading AJAX dropdown pattern as Dharani (District → Mandal → Village → Survey No.).
- Portal occasionally returns Telugu-only content; selectors may contain Telugu text.
- Pattadar (title holder) details are presented in a separate tab/section.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.scrapers.base import BaseScraper, _retry

log = structlog.get_logger()

URL = "https://meebhoomi.ap.gov.in"


class MeebhoomiScraper(BaseScraper):
    """Scrape Andhra Pradesh land records from the MeeBhoomi portal."""

    @_retry
    async def scrape(
        self,
        *,
        district: str,
        mandal: str,
        village: str,
        survey_number: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Return a ``LandRecord``-compatible dict."""
        async with self.get_page() as page:
            await page.goto(URL, wait_until="networkidle")
            log.info("meebhoomi.loaded")

            # Cascading dropdowns
            await self._select_dropdown(page, "#ContentPlaceHolder1_ddlDistrict", district)
            log.info("meebhoomi.district_selected", district=district)

            await self._select_dropdown(page, "#ContentPlaceHolder1_ddlMandal", mandal)
            log.info("meebhoomi.mandal_selected", mandal=mandal)

            await self._select_dropdown(page, "#ContentPlaceHolder1_ddlVillage", village)
            log.info("meebhoomi.village_selected", village=village)

            await self._wait_and_fill(page, "#ContentPlaceHolder1_txtSurveyNo", survey_number)
            await self._wait_and_click(page, "#ContentPlaceHolder1_btnSearch")
            await page.wait_for_load_state("networkidle")
            log.info("meebhoomi.search_submitted")

            return await self._extract_record(page, survey_number)

    async def _extract_record(self, page: Any, survey_number: str) -> dict[str, Any]:
        """Parse the results grid."""
        await page.wait_for_selector(
            "#ContentPlaceHolder1_GridView1, .result-table, #resultDiv",
            timeout=self.DEFAULT_TIMEOUT_MS,
        )

        owner_name = await self._cell_text(page, "#ContentPlaceHolder1_GridView1", 0, 1)
        extent_text = await self._cell_text(page, "#ContentPlaceHolder1_GridView1", 0, 2)
        land_class = await self._cell_text(page, "#ContentPlaceHolder1_GridView1", 0, 3)
        pattadar = await self._cell_text(page, "#ContentPlaceHolder1_GridView1", 0, 4)

        extent_val = "0"
        extent_unit = "acres"
        if extent_text:
            parts = extent_text.split()
            extent_val = parts[0] if parts else "0"
            extent_unit = parts[1] if len(parts) > 1 else "acres"

        return {
            "owner_name": owner_name or "N/A",
            "survey_number": survey_number,
            "extent": extent_val,
            "extent_unit": extent_unit,
            "land_type": land_class or "unknown",
            "pattadar": pattadar or "",
            "mutation_history": [],
        }

    async def _cell_text(self, page: Any, table_sel: str, row: int, col: int) -> str | None:
        """Return text of a specific cell in a GridView table."""
        rows = await page.query_selector_all(f"{table_sel} tr")
        # skip header row
        data_rows = rows[1:] if len(rows) > 1 else rows
        if row < len(data_rows):
            cells = await data_rows[row].query_selector_all("td")
            if col < len(cells):
                return (await cells[col].inner_text()).strip()
        return None
