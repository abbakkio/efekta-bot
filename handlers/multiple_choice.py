from patchright.async_api import Page, Frame
from .base import BaseHandler

class MultipleChoiceHandler(BaseHandler):
    """Detects and selects untried options in multiple-choice, checkboxes, and tap-to-select questions."""

    def _get_enabled_options(self, target: Page | Frame):
        return target.locator(
            'ef-multiple-choice-tap-task-response-option:not(.incorrect) button.option-button:not(.incorrect):not(.is-selected):not(.selected):visible, '
            'button[role="radio"]:not([disabled]):not([aria-disabled="true"]):not(.incorrect):not([class*="incorrect"]):not(.is-selected):not(.selected):visible, '
            'div[role="radio"]:not([disabled]):not([aria-disabled="true"]):not(.incorrect):not([class*="incorrect"]):not(.is-selected):not(.selected):visible, '
            'button[role="checkbox"]:not([disabled]):not([aria-disabled="true"]):not(.incorrect):not([class*="incorrect"]):not(.is-selected):not(.selected):visible, '
            'div[role="checkbox"]:not([disabled]):not([aria-disabled="true"]):not(.incorrect):not([class*="incorrect"]):not(.is-selected):not(.selected):visible, '
            '.option-button:not([disabled]):not([aria-disabled="true"]):not(.incorrect):not([class*="incorrect"]):not(.is-selected):not(.selected):visible, '
            '[data-testid*="choice" i]:not([disabled]):not(.incorrect):not(.is-selected):not(.selected):visible, '
            '[data-testid*="option" i]:not([disabled]):not(.incorrect):not(.is-selected):not(.selected):visible, '
            '.exercise-option:not([disabled]):not(.incorrect):not(.is-selected):not(.selected):visible, '
            '.option-card:not([disabled]):not(.incorrect):not(.is-selected):not(.selected):visible, '
            '.choice-item:not([disabled]):not(.incorrect):not(.is-selected):not(.selected):visible'
        )

    async def can_handle(self, target: Page | Frame) -> bool:
        # If Next or Continue is already enabled, slide is ready to advance
        advance_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button[class*="main-next"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next"), '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Continue"), '
            'button[data-testid*="next" i]:not([disabled]):visible, '
            'button[data-testid*="continue" i]:not([disabled]):visible'
        ).first
        if await advance_btn.count() > 0:
            return False

        options = self._get_enabled_options(target)
        count = await options.count()
        if count == 0:
            return False

        # If Check / Submit button is active, let NavigationHandler click Check
        check_btn = target.locator(
            'button:not([disabled]):visible:has-text("Check"), '
            'button:not([disabled]):visible:has-text("Submit"), '
            'button:not([disabled]):visible[data-testid*="check" i], '
            'button:not([disabled]):visible[data-testid*="submit" i]'
        ).first
        if await check_btn.count() > 0:
            # Check if at least one option is selected
            selected = target.locator(
                '[role="radio"].is-selected:visible, [role="radio"].selected:visible, '
                '[role="checkbox"].is-selected:visible, [role="checkbox"].selected:visible, '
                '.option-button.is-selected:visible, .option-button.selected:visible, '
                '.selected:visible, [aria-checked="true"]:visible'
            )
            if await selected.count() > 0:
                return False

        return True

    async def handle(self, target: Page | Frame) -> bool:
        options = self._get_enabled_options(target)
        count = await options.count()
        if count == 0:
            return False

        target_opt = options.first
        opt_text = (await target_opt.inner_text()).replace('\n', ' ')[:40]
        print(f"  [Choice] Selecting untried option ({count} available): '{opt_text}'...")
        await self.sleep_delay(0.5, 0.8)
        try:
            await target_opt.click()
        except Exception:
            await target_opt.dispatch_event("click")
        await self.sleep_delay(0.8, 1.2)
        return True
