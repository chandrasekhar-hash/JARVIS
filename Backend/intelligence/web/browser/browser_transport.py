"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Browser Transport Abstraction.
Defines BaseBrowserTransport abstract interface and PlaywrightBrowserTransport implementation using Playwright Chromium.
Exposes clean methods for page operations without leaking raw engine handles to reasoning layers.
"""
import abc
import logging
from typing import Optional, Dict, Any, Tuple
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

logger = logging.getLogger("JARVIS_BrowserTransport")


class BaseBrowserTransport(abc.ABC):
    """
    Abstract transport engine interface for browser automation.
    """

    @abc.abstractmethod
    async def initialize(self) -> None:
        pass

    @abc.abstractmethod
    async def open_context(self) -> Any:
        pass

    @abc.abstractmethod
    async def navigate(self, context: Any, url: str) -> Tuple[bool, str, str]:
        pass

    @abc.abstractmethod
    async def observe_html(self, page: Any) -> str:
        pass

    @abc.abstractmethod
    async def click_element(self, page: Any, selector: str) -> bool:
        pass

    @abc.abstractmethod
    async def scroll(self, page: Any, direction: str = "down") -> bool:
        pass

    @abc.abstractmethod
    async def close_context(self, context: Any) -> None:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass


class PlaywrightBrowserTransport(BaseBrowserTransport):
    """
    Playwright Chromium browser transport implementation.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def initialize(self) -> None:
        if not self._playwright:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking"]
            )

    async def open_context(self) -> BrowserContext:
        await self.initialize()
        # Ephemeral context with service workers blocked and permissions revoked
        context = await self._browser.new_context(
            service_workers="block",
            permissions=[],
            accept_downloads=True
        )
        return context

    async def navigate(self, page: Page, url: str) -> Tuple[bool, str, str]:
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            status = response.status if response else 200
            final_url = page.url
            return status < 400, final_url, f"HTTP {status}"
        except Exception as exc:
            logger.warning(f"Browser navigation failed for '{url}': {exc}")
            return False, url, str(exc)

    async def observe_html(self, page: Page) -> str:
        try:
            return await page.content()
        except Exception as exc:
            logger.error(f"Failed to observe page HTML: {exc}")
            return ""

    async def click_element(self, page: Page, selector: str) -> bool:
        try:
            await page.click(selector, timeout=3000)
            return True
        except Exception as exc:
            logger.warning(f"Click failed for selector '{selector}': {exc}")
            return False

    async def scroll(self, page: Page, direction: str = "down") -> bool:
        try:
            delta_y = 500 if direction == "down" else -500
            await page.evaluate(f"window.scrollBy(0, {delta_y})")
            return True
        except Exception as exc:
            logger.warning(f"Scroll failed: {exc}")
            return False

    async def close_context(self, context: BrowserContext) -> None:
        try:
            if context:
                await context.close()
        except Exception as exc:
            logger.warning(f"Error closing context: {exc}")

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
        except Exception as exc:
            logger.warning(f"Error closing playwright transport: {exc}")


playwright_transport = PlaywrightBrowserTransport()
