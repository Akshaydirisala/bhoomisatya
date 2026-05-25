"""Dharani (Telangana) land records scraper.

Portal: https://dharani.telangana.gov.in/homePage

Quirks:
- Notoriously slow and unreliable; frequent 502/504 errors.
- Four cascading AJAX dropdowns (District → Mandal → Village → Survey No.)
  each populated only after the parent selection triggers an XHR.
- CSRF token is carried in a ``setAuth`` cookie; must be forwarded in headers.
- Some pages render inside iframes.
"""

from __future__ import annotations

from typing import Any

import structlog
from playwright.async_api import Page

from src.scrapers.base import BaseScraper, _retry

log = structlog.get_logger()

URL = "https://dharani.telangana.gov.in/homePage"
TIMEOUT_MS = 90_000  # portal is notoriously slow


class DharaniScraper(BaseScraper):
    """Scrape Telangana land records from the Dharani portal."""

    DEFAULT_TIMEOUT_MS = TIMEOUT_MS

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
        """Return a ``LandRecord``-compatible dict for the given survey number."""
        async with self.get_page() as page:
            page.set_default_timeout(TIMEOUT_MS)
            await page.goto(URL, wait_until="networkidle")
            log.info("dharani.loaded")

            # Navigate to the land-data / known-survey search
            await self._navigate_to_search(page)

            # Cascading dropdowns
            await self._select_dropdown(page, "#districtId", district)
            log.info("dharani.district_selected", district=district)

            await self._select_dropdown(page, "#mandalId", mandal)
            log.info("dharani.mandal_selected", mandal=mandal)

            await self._select_dropdown(page, "#villageId", village)
            log.info("dharani.village_selected", village=village)

            await self._wait_and_fill(page, "#surveyNo", survey_number)
            await self._wait_and_click(page, "#btnSearch")
            await page.wait_for_load_state("networkidle")
            log.info("dharani.search_submitted")

            return await self._extract_record(page, survey_number)

    # --- internal helpers ---

    async def _navigate_to_search(self, page: Page) -> None:
        """Click through menus to reach the Known Survey Number search page."""
        # The homepage has a nav link to "Know Your Land Status"
        try:
            await self._wait_and_click(page, "text=Know Your Land Status")
            await page.wait_for_load_state("networkidle")
        except Exception:
            # Fallback: direct navigation
            await page.goto(
                "https://dharani.telangana.gov.in/knowLandStatus",
                wait_until="networkidle",
            )

    async def _extract_csrf(self, page: Page) -> str | None:
        """Extract CSRF token from the setAuth cookie if present."""
        cookies = await page.context.cookies()
        for c in cookies:
            if c["name"] == "setAuth":
                return c["value"]
        return None

    async def _extract_record(self, page: Page, survey_number: str) -> dict[str, Any]:
        """Parse the result table / card that appears after search."""
        await page.wait_for_selector(".result-table, .land-details, #resultDiv", timeout=TIMEOUT_MS)

        # Try structured table first
        owner_name = await self._safe_text(page, ".owner-name, #ownerName")
        father_name = await self._safe_text(page, ".father-name, #fatherName")
        extent_text = await self._safe_text(page, ".extent, #extent")
        land_type = await self._safe_text(page, ".land-type, #landType")

        # Mutation details (may be a sub-table)
        mutation_rows = await page.query_selector_all(".mutation-row, #mutationTable tr")
        mutations: list[dict[str, str]] = []
        for row in mutation_rows:
            cells = await row.query_selector_all("td")
            if len(cells) >= 3:
                mutations.append(
                    {
                        "date": (await cells[0].inner_text()).strip(),
                        "type": (await cells[1].inner_text()).strip(),
                        "details": (await cells[2].inner_text()).strip(),
                    }
                )

        extent_val = "0"
        extent_unit = "acres"
        if extent_text:
            parts = extent_text.split()
            extent_val = parts[0] if parts else "0"
            extent_unit = parts[1] if len(parts) > 1 else "acres"

        return {
            "owner_name": owner_name or "N/A",
            "father_name": father_name or "",
            "survey_number": survey_number,
            "extent": extent_val,
            "extent_unit": extent_unit,
            "land_type": land_type or "unknown",
            "mutation_history": mutations,
        }

    async def _safe_text(self, page: Page, selector: str) -> str | None:
        """Return inner text of the first matching element, or None."""
        el = await page.query_selector(selector)
        if el:
            return (await el.inner_text()).strip()
        return None
