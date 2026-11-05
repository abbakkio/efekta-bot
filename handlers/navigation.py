import asyncio
from patchright.async_api import Page, Frame
from .base import BaseHandler

class NavigationHandler(BaseHandler):
    """Handles transitions: Dialogs, Step start, Check/Submit answer, Next/Continue slide."""

    def __init__(self):
        super().__init__()
        self._consecutive_dialogs = 0
        self._consecutive_nexts = 0
        self._last_state_signature = None

    def reset_circuit_breakers(self):
        """Resets click counters when another handler (choice, input, media) acts."""
        self._consecutive_dialogs = 0
        self._consecutive_nexts = 0

    def _get_dialog_button(self, target: Page | Frame):
        return target.locator(
            'button:not([disabled]):visible:has-text("Okay, got it"), '
            'button:not([disabled]):visible:has-text("Got it"), '
            'button:not([disabled]):visible:has-text("I understand"), '
            'button:not([disabled]):visible:has-text("Understood")'
        ).first

    def _get_finish_skipped_button(self, target: Page | Frame):
        return target.locator(
            'button:not([disabled]):visible:has-text("Finish skipped tasks"), '
            'button:not([disabled]):visible:has-text("Finish skipped activities"), '
            'button:not([disabled]):visible:has-text("Finish skipped"), '
            'button:not([disabled]):visible:has-text("Retry activity"), '
            'button:not([disabled]):visible:has-text("Retry step")'
        ).first

    def _get_step_button(self, target: Page | Frame):
        return target.locator(
            'button:not([disabled]):visible:has-text("Start next step"), '
            'button:not([disabled]):visible:has-text("Next step"), '
            'button:not([disabled]):visible:has-text("Start step"), '
            'button:not([disabled]):visible:has-text("Start activity"), '
            'button:not([disabled]):visible:has-text("Continue to next step"), '
            'div[role="button"][aria-label*="status started" i]:visible, '
            'div[role="button"][aria-label*="status in progress" i]:visible, '
            'div[role="button"][aria-label*="status not started" i]:visible, '
            'div[role="button"][aria-label*="status"]:not([aria-label*="status passed"]):visible'
        ).first

    def _get_check_button(self, target: Page | Frame):
        return target.locator(
            'button:not([disabled]):visible:has-text("Check"), '
            'button:not([disabled]):visible:has-text("Submit"), '
            'button:not([disabled]):visible[data-testid*="check" i], '
            'button:not([disabled]):visible[data-testid*="submit" i]'
        ).first

    def _get_close_lesson_button(self, target: Page | Frame):
        return target.locator(
            'button:not([disabled]):visible[aria-label*="Close lesson" i], '
            'button:not([disabled]):visible:has-text("Return to unit overview")'
        ).first

    def _get_next_button(self, target: Page | Frame):
        return target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button[class*="main-next"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next"), '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Continue"), '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Finish"), '
            'button:not([disabled]):visible:has-text("Back to lesson overview"), '
            'a:visible:has-text("Back to lesson overview"), '
            'button:not([disabled]):visible[data-testid*="next" i], '
            'button:not([disabled]):visible[data-testid*="continue" i]'
        ).first

    def _get_incomplete_activity_button(self, target: Page | Frame):
        """Returns the next incomplete activity tab in a multi-activity step."""
        return target.locator(
            'div.wp[aria-label*="Step navigation, Activity"]:not([aria-label*="complete"]):not(.selected)'
        ).first

    def _get_step_summary_tab(self, target: Page | Frame):
        """Returns the Step summary tab if available."""
        return target.locator('div.wp[aria-label*="Step summary"]:not(.selected)').first

    async def _is_unpassed_summary(self, target: Page | Frame) -> bool:
        """Checks if the current view is a summary of an unpassed STEP."""
        indicators = target.locator(r'text=/Step not passed|Pass at least \d+ activities/i')
        return await indicators.count() > 0 and await indicators.first.is_visible()

    async def _ensure_scrolled_to_bottom(self, target: Page | Frame):
        """Scrolls any active task container or reading area to the bottom/end to unlock Next button."""
        try:
            await target.evaluate("""() => {
                const scrollers = Array.from(document.querySelectorAll(
                    '[cdkscrollable], .task-area, .content-area, ef-task-layout, main, .flashcard-list, .flashcards-container, [class*="scroll"], [class*="container"]'
                ));
                for (const s of scrollers) {
                    if (s.scrollHeight > s.clientHeight) {
                        s.scrollTop = s.scrollHeight;
                        s.dispatchEvent(new Event('scroll'));
                    }
                    if (s.scrollWidth > s.clientWidth) {
                        s.scrollLeft = s.scrollWidth;
                        s.dispatchEvent(new Event('scroll'));
                    }
                }
                const observers = Array.from(document.querySelectorAll('[ef-visibility-observer]'));
                for (const obs of observers) {
                    obs.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
                }
            }""")
        except Exception:
            pass

    async def can_handle(self, target: Page | Frame) -> bool:
        await self._ensure_scrolled_to_bottom(target)
        if await self._get_dialog_button(target).count() > 0:
            return True
        if await self._get_finish_skipped_button(target).count() > 0:
            return True
        if await self._get_check_button(target).count() > 0:
            return True
        if await self._get_next_button(target).count() > 0:
            return True
        if await self._get_step_button(target).count() > 0:
            return True
        if await self._get_close_lesson_button(target).count() > 0:
            all_steps_passed = await target.evaluate("""() => {
                const steps = Array.from(document.querySelectorAll('div[role="button"][aria-label*="status"]'));
                if (steps.length === 0) return false;
                return steps.every(s => (s.getAttribute('aria-label') || '').includes('status passed'));
            }""")
            is_passed = target.locator('text=/Pass|Retake lesson|Lesson passed/').first
            if all_steps_passed or (await is_passed.count() > 0 and await is_passed.is_visible()):
                return True
        return False

    async def handle(self, target: Page | Frame) -> bool:
        try:
            task_header = target.locator('text=/Task \\d+ of \\d+/i').first
            sig = await task_header.inner_text() if await task_header.count() > 0 else None
            if sig and sig != self._last_state_signature:
                self._last_state_signature = sig
                self._consecutive_nexts = 0
                self._consecutive_dialogs = 0
        except Exception:
            pass

        # 1. Dialogs (e.g. "Okay, got it")
        dialog_btn = self._get_dialog_button(target)
        if await dialog_btn.count() > 0:
            self._consecutive_dialogs += 1
            if self._consecutive_dialogs > 3:
                print("  [Navigation] Circuit breaker: Detected repeated dialog prompt. Pausing automatic dismissal.")
                return False
            print("  [Navigation] Dismissing informational dialog...")
            await self.sleep_delay(0.5, 1.0)
            await dialog_btn.click()
            await self.sleep_delay(0.5, 1.0)
            return True
        else:
            self._consecutive_dialogs = 0

        # 2. Check / Submit answer
        check_btn = self._get_check_button(target)
        if await check_btn.count() > 0:
            self._consecutive_nexts = 0
            print("  [Navigation] Clicking 'Check / Submit'...")
            await self.sleep_delay(0.5, 1.2)
            await check_btn.click()
            await self.sleep_delay(0.5, 1.0)
            return True

        # 3. Lesson overview passed -> close lesson and return to dashboard
        close_btn = self._get_close_lesson_button(target)
        if await close_btn.count() > 0:
            all_steps_passed = await target.evaluate("""() => {
                const steps = Array.from(document.querySelectorAll('div[role="button"][aria-label*="status"]'));
                if (steps.length === 0) return false;
                return steps.every(s => (s.getAttribute('aria-label') || '').includes('status passed'));
            }""")
            is_passed = target.locator('text=/Pass|Retake lesson|Lesson passed/').first
            has_pass_badge = await is_passed.count() > 0 and await is_passed.is_visible()
            if all_steps_passed or has_pass_badge:
                print("  [Navigation] All lesson steps passed! Closing lesson view to return to course dashboard...")
                await self.sleep_delay(0.5, 1.0)
                await close_btn.click()
                await self.sleep_delay(2.5, 3.5)
                return True

        # 4. Step launcher buttons (e.g. "Start next step" when step is passed)
        step_btn = self._get_step_button(target)
        if await step_btn.count() > 0:
            aria = await step_btn.get_attribute("aria-label") or "Next step"
            print(f"  [Navigation] Launching step: {aria[:40]}...")
            await self.sleep_delay(0.5, 1.0)
            await step_btn.click()
            await self.sleep_delay(1.0, 1.5)
            self._consecutive_nexts = 0
            return True

        # 5. Check if the activity explicitly failed to reach passing score and needs retry
        is_unpassed = await target.locator('text=/Activity: Not passed|Step not passed/i').count() > 0
        finish_skipped = self._get_finish_skipped_button(target)
        if is_unpassed and await finish_skipped.count() > 0:
            txt = (await finish_skipped.inner_text()).strip()
            print(f"  [Navigation] Activity/Step not passed. Clicking '{txt}' to achieve required passing score...")
            await self.sleep_delay(0.5, 1.0)
            try:
                await finish_skipped.click(timeout=3000)
            except Exception:
                await finish_skipped.dispatch_event("click")
            await self.sleep_delay(1.0, 1.5)
            self._consecutive_nexts = 0
            return True

        # 6. Next / Continue button (prioritize moving forward when passed)
        next_btn = self._get_next_button(target)
        if await next_btn.count() > 0:
            btn_text = (await next_btn.inner_text()).strip()
            self._consecutive_nexts += 1
            if self._consecutive_nexts > 8:
                print(f"  [Navigation] Circuit breaker: '{btn_text}' clicked repeatedly without progress.")
                return False

            print(f"  [Navigation] Clicking '{btn_text}'...")
            await self.sleep_delay(0.5, 1.0)
            try:
                await next_btn.click()
            except Exception:
                await next_btn.dispatch_event("click")
            await self.sleep_delay(1.0, 1.5)
            return True

        # 7. Fallback Finish skipped tasks / retry (when Next is not available)
        if await finish_skipped.count() > 0:
            txt = (await finish_skipped.inner_text()).strip()
            print(f"  [Navigation] Clicking '{txt}' to complete required activity...")
            await self.sleep_delay(0.5, 1.0)
            try:
                await finish_skipped.click(timeout=3000)
            except Exception:
                await finish_skipped.dispatch_event("click")
            await self.sleep_delay(1.0, 1.5)
            self._consecutive_nexts = 0
            return True

        return False
