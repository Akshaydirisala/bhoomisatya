"""eCourts India scraper.

Portal: https://ecourts.gov.in/ecourts_home/

Quirks:
- Every search is guarded by a Securimage CAPTCHA.
- If ``captcha_solver_api_key`` is provided we delegate to a solving service;
  otherwise we raise an error asking the caller to provide one.
- Party-name search flow: State → District → Court Complex → Party Name → Year.
- Alternative: commercial APIs (CaseMine, Legitquest) at ~Rs 2-5/search.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.scrapers.base import BaseScraper, _retry

log = structlog.get_logger()

URL = "https://ecourts.gov.in/ecourts_home/"


class ECourtsScraper(BaseScraper):
    """Search eCourts for litigation records by party name."""

    def __init__(
        self,
        *,
        headless: bool = True,
        proxy_url: str | None = None,
        captcha_solver_api_key: str | None = None,
    ) -> None:
        super().__init__(headless=headless, proxy_url=proxy_url)
        self.captcha_solver_api_key = captcha_solver_api_key

    @_retry
    async def scrape(
        self,
        *,
        state: str,
        district: str,
        court_complex: str | None = None,
        party_name: str,
        year: str | None = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Return a list of ``CourtCase``-compatible dicts."""
        if not self.captcha_solver_api_key:
            raise RuntimeError(
                "eCourts requires CAPTCHA solving. Provide captcha_solver_api_key or "
                "use a commercial API (CaseMine / Legitquest) instead."
            )

        async with self.get_page() as page:
            await page.goto(URL, wait_until="networkidle")
            log.info("ecourts.loaded")

            # Navigate to party name search
            await self._wait_and_click(page, "text=Party Name")
            await page.wait_for_load_state("networkidle")

            # Cascading selectors
            await self._select_dropdown(page, "#sess_state_code", state)
            await self._select_dropdown(page, "#sess_dist_code", district)
            if court_complex:
                await self._select_dropdown(page, "#court_complex_code", court_complex)

            await self._wait_and_fill(page, "#petres_name", party_name)

            if year:
                await self._wait_and_fill(page, "#rgyear", year)

            # Solve CAPTCHA
            captcha_text = await self._solve_captcha(page)
            await self._wait_and_fill(page, "#captcha", captcha_text)

            await self._wait_and_click(page, "#searchbtn, #submitButton")
            await page.wait_for_load_state("networkidle")
            log.info("ecourts.search_submitted")

            return await self._extract_results(page)

    async def _solve_captcha(self, page: Any) -> str:
        """Capture the CAPTCHA image and solve via external API."""
        import httpx

        captcha_el = await page.query_selector("#captcha_image, img[alt='Captcha']")
        if not captcha_el:
            raise RuntimeError("CAPTCHA image element not found")

        captcha_bytes = await captcha_el.screenshot()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anti-captcha.com/createTask",
                json={
                    "clientKey": self.captcha_solver_api_key,
                    "task": {
                        "type": "ImageToTextTask",
                        "body": __import__("base64").b64encode(captcha_bytes).decode(),
                    },
                },
                timeout=30,
            )
            data = resp.json()
            task_id = data.get("taskId")
            if not task_id:
                raise RuntimeError(f"CAPTCHA task creation failed: {data}")

            # Poll for result
            import asyncio

            for _ in range(20):
                await asyncio.sleep(3)
                res = await client.post(
                    "https://api.anti-captcha.com/getTaskResult",
                    json={"clientKey": self.captcha_solver_api_key, "taskId": task_id},
                    timeout=10,
                )
                result = res.json()
                if result.get("status") == "ready":
                    return result["solution"]["text"]

            raise RuntimeError("CAPTCHA solving timed out")

    async def _extract_results(self, page: Any) -> dict[str, Any]:
        """Parse the case-list results table."""
        await page.wait_for_selector(
            "table, #dispTable, .case_table", timeout=self.DEFAULT_TIMEOUT_MS
        )

        rows = await page.query_selector_all("#dispTable tr, table.case_table tr, table tbody tr")
        cases: list[dict[str, Any]] = []
        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) < 3:
                continue
            texts = [(await c.inner_text()).strip() for c in cells]
            cases.append(
                {
                    "case_number": texts[0] if texts else "",
                    "parties": texts[1] if len(texts) > 1 else "",
                    "court": texts[2] if len(texts) > 2 else "",
                    "status": texts[3] if len(texts) > 3 else "",
                    "filing_date": texts[4] if len(texts) > 4 else None,
                    "next_hearing": texts[5] if len(texts) > 5 else None,
                    "case_type": texts[6] if len(texts) > 6 else None,
                }
            )

        return {"cases": cases}
