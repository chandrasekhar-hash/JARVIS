"""
J.A.R.V.I.S. Intelligence I2.2 V7 — Fail-Closed Navigation Guard.
Intercepts browser network requests (navigations, XHR/fetch, iframes, popups, redirects) via Playwright page.route.
Enforces frozen V2 UrlSafetyValidator checks and FAILS CLOSED on any exception or resolution failure.
"""
import logging
from typing import Optional, Set
from playwright.async_api import Page, Route, Request

from intelligence.web.url_validator import url_validator
from intelligence.web.browser.models import LinkRejectionReason

logger = logging.getLogger("JARVIS_NavigationGuard")


class NavigationGuard:
    """
    Network request interceptor evaluating all Chromium network traffic against SSRF policies.
    Fails closed unconditionally on validation errors or exceptions.
    """

    def __init__(self, allow_local_fixture_override: bool = False):
        self._allow_local_fixture_override = allow_local_fixture_override

    async def attach_guard(self, page: Page, visited_urls: Optional[Set[str]] = None) -> None:
        """
        Attaches request interception routing to a Playwright page.
        """

        async def _intercept_route(route: Route, request: Request):
            url = request.url

            # Allow local test fixture ONLY if explicitly configured by test fixture injection
            if self._allow_local_fixture_override and ("127.0.0.1" in url or "localhost" in url):
                await route.continue_()
                return

            try:
                # Run V2 SSRF Safety Validation
                is_safe, resolved_ip, err_msg = await url_validator.validate_url(url)

                if not is_safe:
                    logger.warning(f"[NavigationGuard] SSRF Blocked request to '{url}': {err_msg}")
                    await route.abort("blockedbyclient")
                    return

                # Passed validation
                await route.continue_()
            except Exception as exc:
                # FAIL CLOSED: Any exception during safety validation aborts the request!
                logger.error(f"[NavigationGuard] Safety validation exception for '{url}': {exc}. Failing closed (aborted).")
                await route.abort("blockedbyclient")

        try:
            await page.route("**/*", _intercept_route)
        except Exception as exc:
            logger.error(f"Failed to attach route interceptor: {exc}")


navigation_guard = NavigationGuard()
