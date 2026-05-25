"""Base scraper with Playwright browser management and retry logic."""

from __future__ import annotations

import abc
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any

import structlog
from playwright.async_api import Browser, Page, async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

log = structlog.get_logger()


def _retry(fn):  # noqa: ANN001, ANN202
    """Decorator: 3 retries with exponential backoff."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await fn(*args, **kwargs)

    return wrapper


class BaseScraper(abc.ABC):
    """Async Playwright-based scraper with browser pool, retry, and helper methods.

    Manages a single Chromium browser instance configured for Indian locale/timezone.
    Subclasses implement ``scrape()`` to interact with a specific government portal.
    """

    DEFAULT_TIMEOUT_MS = 60_000

    def __init__(self, *, headless: bool = True, proxy_url: str | None = None) -> None:
        self.headless = headless
        self.proxy_url = proxy_url
        self._playwright: Any | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        """Launch Chromium with Indian locale and Asia/Kolkata timezone."""
        self._playwright = await async_playwright().start()
        launch_kwargs: dict[str, Any] = {"headless": self.headless}
        if self.proxy_url:
            launch_kwargs["proxy"] = {"server": self.proxy_url}
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        log.info("browser.started", headless=self.headless)

    async def stop(self) -> None:
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        log.info("browser.stopped")

    @asynccontextmanager
    async def get_page(self) -> AsyncGenerator[Page, None]:
        """Yield a new page in an Indian-locale browser context."""
        if not self._browser:
            raise RuntimeError("Browser not started – call start() first")
        context = await self._browser.new_context(
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            ignore_https_errors=True,
        )
        page = await context.new_page()
        page.set_default_timeout(self.DEFAULT_TIMEOUT_MS)
        try:
            yield page
        finally:
            await context.close()

    # --- helper methods ---

    async def _wait_and_click(self, page: Page, selector: str) -> None:
        await page.wait_for_selector(selector, state="visible")
        await page.click(selector)

    async def _wait_and_fill(self, page: Page, selector: str, value: str) -> None:
        await page.wait_for_selector(selector, state="visible")
        await page.fill(selector, value)

    async def _wait_for_selector(self, page: Page, selector: str) -> None:
        await page.wait_for_selector(selector, state="visible")

    async def _select_dropdown(self, page: Page, selector: str, value: str) -> None:
        """Select a dropdown value and wait for any triggered AJAX to settle."""
        await page.wait_for_selector(selector, state="visible")
        await page.select_option(selector, value)
        # Wait for potential AJAX spinners / network idle
        await page.wait_for_load_state("networkidle")

    # --- abstract ---

    @abc.abstractmethod
    async def scrape(self, **kwargs: Any) -> dict[str, Any]:
        """Run the scrape and return a schema-compatible dict."""
        ...
