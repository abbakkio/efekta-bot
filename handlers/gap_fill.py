import asyncio
from patchright.async_api import Page, Frame
from .base import BaseHandler

class GapFillHandler(BaseHandler):
    """Handles fill-in-the-gap exercises with bottom-drawer options."""

    def __init__(self):
        super().__init__()
        self._attempt_idx = 0
        self._last_blanks_count = -1

    def _get_available_drawer_options(self, target: Page | Frame):
        return target.locator(".drawer-option:not([class*='incorrect']):not([aria-disabled='true']):visible")

    def _get_blanks(self, target: Page | Frame):
        return target.locator(".selection-gap-button:not([disabled]):visible, [aria-label*='Blank' i]:not([disabled]):visible")

    async def can_handle(self, target: Page | Frame) -> bool:
        # Check if drawer options are currently open
        if await self._get_available_drawer_options(target).count() > 0:
            return True

        # Check if there are unfilled blanks
        blanks = self._get_blanks(target)
        if await blanks.count() > 0:
            advance_btn = target.locator(
                'button:not([disabled]):visible:has-text("Next"), '
                'button:not([disabled]):visible:has-text("Continue"), '
                'button:not([disabled]):visible:has-text("Check")'
            ).first
            if await advance_btn.count() > 0:
                return False
            return True

        return False

    async def handle(self, target: Page | Frame) -> bool:
        blanks = self._get_blanks(target)
        blanks_count = await blanks.count()

        # If a blank was recently filled, reset rotation
        if self._last_blanks_count != -1 and blanks_count < self._last_blanks_count:
            self._attempt_idx = 0
        self._last_blanks_count = blanks_count

        # 1. If drawer options are visible, pick with rotating index
        drawer_opts = self._get_available_drawer_options(target)
        opts_count = await drawer_opts.count()
        if opts_count > 0:
            idx = self._attempt_idx % opts_count
            opt = drawer_opts.nth(idx)
            txt = (await opt.inner_text()).replace("\n", " ").strip()
            print(f"  [GapFill] Selecting option [{idx+1}/{opts_count}]: {txt[:30]}...")
            await self.sleep_delay(0.4, 0.7)
            await opt.click()
            self._attempt_idx += 1
            await asyncio.sleep(1.2)
            return True

        # 2. Otherwise click the first unfilled blank
        if blanks_count > 0:
            blank = blanks.first
            print(f"  [GapFill] Opening blank (remaining: {blanks_count})...")
            await blank.scroll_into_view_if_needed()
            await self.sleep_delay(0.4, 0.6)
            await blank.click()
            await asyncio.sleep(1.0)
            return True

        return False


