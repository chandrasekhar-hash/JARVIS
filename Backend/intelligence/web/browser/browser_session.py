"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Ephemeral Browser Session Manager.
Manages isolated Playwright browser contexts, revoking permissions, blocking service workers,
handling download cancellations/handoffs, auto-dismissing dialogs, enforcing MAX_BROWSER_PAGES=2 popup limits,
and clearing cookies/storage on session teardown.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import BrowserContext, Page, Download, Dialog

from intelligence.web.structured.models import ResourceCandidate
from intelligence.web.browser.models import BrowserConfig, LinkRejectionReason
from intelligence.web.browser.browser_transport import BaseBrowserTransport
from intelligence.web.browser.navigation_guard import NavigationGuard

logger = logging.getLogger("JARVIS_BrowserSession")


class EphemeralBrowserSession:
    """
    Isolated request-scoped browser session lifecycle manager.
    """

    def __init__(self, transport: BaseBrowserTransport, guard: NavigationGuard):
        self._transport = transport
        self._guard = guard
        self._context: Optional[BrowserContext] = None
        self._pages: List[Page] = []
        self._discovered_downloads: List[ResourceCandidate] = []

    async def start_session(self) -> Page:
        """
        Starts an isolated Playwright browser context and returns the main Page.
        """
        self._context = await self._transport.open_context()

        # Listen for popup / new tab creation & enforce MAX_BROWSER_PAGES = 2
        self._context.on("page", self._on_page_created)

        main_page = await self._context.new_page()
        self._pages.append(main_page)

        # Attach navigation guard and event handlers
        await self._configure_page_handlers(main_page)
        return main_page

    async def _configure_page_handlers(self, page: Page) -> None:
        """
        Attaches navigation guard, dialog handlers, and download handlers to page.
        """
        # 1. Attach navigation guard
        await self._guard.attach_guard(page)

        # 2. Auto-dismiss modal dialogs (alert, confirm, prompt, beforeunload)
        page.on("dialog", lambda dialog: self._handle_dialog(dialog))

        # 3. Intercept direct click-triggered downloads
        page.on("download", lambda download: self._handle_download(download))

    def _handle_dialog(self, dialog: Dialog) -> None:
        logger.info(f"[BrowserSession] Auto-dismissing modal dialog ({dialog.type}): {dialog.message}")
        try:
            # Asynchronously dismiss dialog
            import asyncio
            asyncio.create_task(dialog.dismiss())
        except Exception as exc:
            logger.warning(f"Error dismissing dialog: {exc}")

    def _handle_download(self, download: Download) -> None:
        logger.info(f"[BrowserSession] Download triggered: {download.url}")
        url = download.url
        filename = download.suggested_filename

        ext = os.path.splitext(filename)[1].lower() if filename else ""
        is_pdf = ext == ".pdf"
        is_executable = ext in (".exe", ".dmg", ".sh", ".pkg", ".bat", ".apk", ".msi")

        rejection_reason = LinkRejectionReason.NONE
        handoff_target = None
        if is_executable:
            rejection_reason = LinkRejectionReason.OVER_BUDGET
        elif is_pdf:
            handoff_target = "I2.3_DOCUMENT_INTELLIGENCE"

        res_candidate = ResourceCandidate(
            url=url,
            canonical_url=url,
            resource_type=ext[1:].upper() if ext else "FILE",
            mime_type="application/octet-stream",
            anchor_text=filename,
            source_id="download_event",
            is_url_safe=not is_executable,
            is_eligible=not is_executable,
            rejection_reason=rejection_reason,
            handoff_target=handoff_target,
        )
        self._discovered_downloads.append(res_candidate)

        # Immediately cancel/delete temporary download artifact
        try:
            import asyncio
            asyncio.create_task(download.cancel())
        except Exception as exc:
            logger.warning(f"Error cancelling download: {exc}")

    def _on_page_created(self, page: Page) -> None:
        """
        Enforces MAX_BROWSER_PAGES = 2 atomically on popup creation.
        """
        if len(self._pages) >= BrowserConfig.MAX_BROWSER_PAGES:
            logger.warning(f"[BrowserSession] Exceeded MAX_BROWSER_PAGES limit ({BrowserConfig.MAX_BROWSER_PAGES}). Closing popup immediately.")
            import asyncio
            asyncio.create_task(page.close())
        else:
            self._pages.append(page)
            import asyncio
            asyncio.create_task(self._configure_page_handlers(page))

    async def close_session(self) -> None:
        """
        Clears storage, cookies, closes pages and context safely.
        """
        try:
            if self._context:
                # Clear cookies and storage
                try:
                    await self._context.clear_cookies()
                except Exception:
                    pass
                await self._transport.close_context(self._context)
                self._context = None
            self._pages.clear()
        except Exception as exc:
            logger.warning(f"Error during browser session teardown: {exc}")

    @property
    def discovered_downloads(self) -> List[ResourceCandidate]:
        return self._discovered_downloads
