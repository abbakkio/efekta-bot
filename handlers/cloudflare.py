import asyncio
from patchright.async_api import Page
from .base import BaseHandler

class CloudflareHandler(BaseHandler):
    """Detects Cloudflare Turnstile or Managed Challenge verification and alerts the user."""

    async def can_handle(self, page: Page) -> bool:
        try:
            url_lower = page.url.lower()
            if "catalyst-enter" in url_lower:
                cf_box = page.locator('iframe[src*="cloudflare" i], iframe[src*="turnstile" i], text="Verification failed", text="Troubleshoot"').first
                if await cf_box.count() > 0 and await cf_box.is_visible():
                    return True

            title = (await page.title()).lower()
            if "just a moment" in title or "attention required" in title:
                return True

            for frame in page.frames:
                if "cloudflare" in frame.url.lower() or "turnstile" in frame.url.lower():
                    return True
        except Exception:
            pass

        return False

    async def handle(self, page: Page) -> bool:
        failed_el = page.locator('text="Verification failed", text="Troubleshoot"').first
        if await failed_el.count() > 0 and await failed_el.is_visible():
            print("  [Cloudflare] Verification failed on screen. Please reload the tab or complete the challenge manually in Chrome.")
            await asyncio.sleep(3.0)
            return True

        print("  [Cloudflare] Cloudflare verification in progress. Please complete any verification prompt in your open Chrome window...")
        await asyncio.sleep(3.0)
        return True

