"""IGRS (Inspector General of Registration & Stamps) scraper.

Supports both Telangana and Andhra Pradesh portals for:
1. Encumbrance Certificate (EC) search
2. Guideline / market value lookup
3. Recent registrations (comparable sales data)

Quirks:
- TS URL: https://registration.telangana.gov.in/ecSearch.htm
- AP URL: https://registration.ap.gov.in/ecSearch.htm
- The EC search page uses cascading dropdowns (District → SRO → Village) plus
  survey number and date range inputs.
- Guideline value pages are on separate paths and vary by state.
"""

from __future__ import annotations

from typing import Any, Literal

import structlog

from src.scrapers.base import BaseScraper, _retry

log = structlog.get_logger()

URLS = {
    "telangana": {
        "ec": "https://registration.telangana.gov.in/ecSearch.htm",
        "guideline": "https://registration.telangana.gov.in/guidelineValue.htm",
    },
    "andhra_pradesh": {
        "ec": "https://registration.ap.gov.in/ecSearch.htm",
        "guideline": "https://registration.ap.gov.in/guidelineValue.htm",
    },
}


class IGRSScraper(BaseScraper):
    """Encumbrance search, guideline values, and comparable sales from IGRS portals."""

    @_retry
    async def scrape(
        self,
        *,
        mode: Literal["encumbrance_search", "guideline_value"] = "encumbrance_search",
        state: Literal["telangana", "andhra_pradesh"] = "telangana",
        district: str,
        sro: str | None = None,
        mandal: str | None = None,
        village: str,
        survey_number: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Return ``EncumbranceRecord`` list or ``ValuationData``-compatible dict."""
        if mode == "encumbrance_search":
            return await self._ec_search(
                state=state,
                district=district,
                sro=sro or "",
                village=village,
                survey_number=survey_number or "",
                from_date=from_date or "",
                to_date=to_date or "",
            )
        return await self._guideline_value(
            state=state, district=district, mandal=mandal or "", village=village
        )

    async def _ec_search(
        self,
        *,
        state: str,
        district: str,
        sro: str,
        village: str,
        survey_number: str,
        from_date: str,
        to_date: str,
    ) -> dict[str, Any]:
        url = URLS[state]["ec"]
        async with self.get_page() as page:
            await page.goto(url, wait_until="networkidle")
            log.info("igrs.ec.loaded", state=state)

            await self._select_dropdown(page, "#district, #ddlDistrict", district)
            if sro:
                await self._select_dropdown(page, "#sro, #ddlSRO", sro)
            await self._wait_and_fill(page, "#village, #txtVillage", village)
            if survey_number:
                await self._wait_and_fill(page, "#surveyNo, #txtSurveyNo", survey_number)
            if from_date:
                await self._wait_and_fill(page, "#fromDate, #txtFromDate", from_date)
            if to_date:
                await self._wait_and_fill(page, "#toDate, #txtToDate", to_date)

            await self._wait_and_click(page, "#btnSearch, input[type='submit']")
            await page.wait_for_load_state("networkidle")
            log.info("igrs.ec.search_submitted")

            # Parse EC results table
            await page.wait_for_selector("table, #resultTable", timeout=self.DEFAULT_TIMEOUT_MS)
            rows = await page.query_selector_all("table tbody tr, #resultTable tr")
            records: list[dict[str, Any]] = []
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 3:
                    continue
                texts = [(await c.inner_text()).strip() for c in cells]
                records.append(
                    {
                        "document_number": texts[0] if texts else "",
                        "document_type": texts[1] if len(texts) > 1 else "",
                        "parties": texts[2] if len(texts) > 2 else "",
                        "registration_date": texts[3] if len(texts) > 3 else None,
                        "sro_name": texts[4] if len(texts) > 4 else None,
                    }
                )

            return {"encumbrance_records": records}

    async def _guideline_value(
        self,
        *,
        state: str,
        district: str,
        mandal: str,
        village: str,
    ) -> dict[str, Any]:
        url = URLS[state]["guideline"]
        async with self.get_page() as page:
            await page.goto(url, wait_until="networkidle")
            log.info("igrs.guideline.loaded", state=state)

            await self._select_dropdown(page, "#district, #ddlDistrict", district)
            if mandal:
                await self._select_dropdown(page, "#mandal, #ddlMandal", mandal)
            await self._select_dropdown(page, "#village, #ddlVillage", village)

            await self._wait_and_click(page, "#btnSearch, input[type='submit']")
            await page.wait_for_load_state("networkidle")
            log.info("igrs.guideline.search_submitted")

            await page.wait_for_selector("table, #resultTable", timeout=self.DEFAULT_TIMEOUT_MS)

            # Extract guideline value
            value_el = await page.query_selector(
                ".guideline-value, #guidelineValue, table tbody tr td:nth-child(2)"
            )
            value_text = (await value_el.inner_text()).strip() if value_el else "0"

            unit_el = await page.query_selector(".unit, #unit, table tbody tr td:nth-child(3)")
            unit_text = (await unit_el.inner_text()).strip() if unit_el else "sq_yard"

            # Comparable sales from recent registrations
            comparable_rows = await page.query_selector_all(".comparable-row, #comparableTable tr")
            comparables: list[dict[str, Any]] = []
            for row in comparable_rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 4:
                    continue
                texts = [(await c.inner_text()).strip() for c in cells]
                comparables.append(
                    {
                        "survey_number": texts[0],
                        "village": texts[1] if len(texts) > 1 else village,
                        "extent": texts[2] if len(texts) > 2 else "0",
                        "sale_value": texts[3] if len(texts) > 3 else "0",
                        "registration_date": texts[4] if len(texts) > 4 else None,
                    }
                )

            return {
                "guideline_value_per_unit": value_text,
                "unit": unit_text,
                "comparable_sales": comparables,
            }
