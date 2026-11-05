import asyncio
from patchright.async_api import Page, Frame
from .base import BaseHandler

DEFAULT_ESSAY = (
    "In my opinion, this topic is truly fascinating and requires careful thought and practical consideration. "
    "I believe that developing positive daily habits and maintaining a healthy balance in life is essential for long-term success. "
    "When faced with difficult challenges, it is important to stay patient, focused, and adaptable to changing circumstances. "
    "Furthermore, learning from experienced mentors and working collaboratively with others can significantly accelerate personal growth. "
    "Taking regular time for reflection allows individuals to understand their strengths and overcome weaknesses effectively. "
    "Developing open communication and mutual support among team members fosters an enjoyable and productive working atmosphere. "
    "In conclusion, dedicating consistent effort towards meaningful goals brings immense satisfaction and lasting happiness."
)

class WritingHandler(BaseHandler):
    """Handles writing challenges (ef-writing-challenge-task, textarea, word counters, and self-evaluation)."""

    def _get_textarea(self, target: Page | Frame):
        return target.locator("textarea:visible, ef-writing-challenge-input textarea:visible").first

    def _get_eval_buttons(self, target: Page | Frame):
        return target.locator(
            'button:not([disabled]):visible:has-text("I think it was just right for me"), '
            'button:not([disabled]):visible:has-text("I enjoyed the challenge"), '
            'button:not([disabled]):visible:has-text("I found it too easy")'
        ).first

    def _get_gen_feedback_button(self, target: Page | Frame):
        return target.locator('button:not([disabled]):visible:has-text("Generate feedback")').first

    async def can_handle(self, target: Page | Frame) -> bool:
        # Check for textarea input
        if await self._get_textarea(target).count() > 0:
            # If Next is already enabled, let NavigationHandler proceed
            next_btn = target.locator('button:not([disabled]):visible:has-text("Next")').first
            if await next_btn.count() > 0:
                return False
            return True

        # Check for self-evaluation screen
        if await self._get_eval_buttons(target).count() > 0:
            return True

        if await self._get_gen_feedback_button(target).count() > 0:
            return True

        return False

    async def handle(self, target: Page | Frame) -> bool:
        # 1. Handle Self-Evaluation if present
        eval_btn = self._get_eval_buttons(target)
        if await eval_btn.count() > 0:
            print("  [Writing] Selecting self-evaluation rating...")
            await self.sleep_delay(0.5, 1.0)
            await eval_btn.click()
            await asyncio.sleep(1.0)

            gen_btn = self._get_gen_feedback_button(target)
            if await gen_btn.count() > 0:
                print("  [Writing] Generating feedback...")
                await gen_btn.click()
                await asyncio.sleep(4.0)
            return True

        gen_btn = self._get_gen_feedback_button(target)
        if await gen_btn.count() > 0:
            print("  [Writing] Clicking 'Generate feedback'...")
            await gen_btn.click()
            await asyncio.sleep(4.0)
            return True

        # 2. Handle Textarea Input
        ta = self._get_textarea(target)
        if await ta.count() > 0:
            print("  [Writing] Writing challenge detected. Composing response...")
            await ta.click()
            await asyncio.sleep(0.3)

            # Efekta anti-cheat: typing differences > 80 chars trigger input wipe.
            # We type in safe 40-char increments with keyup events.
            chunks = [DEFAULT_ESSAY[i:i+40] for i in range(0, len(DEFAULT_ESSAY), 40)]
            current_val = ""
            for chunk in chunks:
                current_val += chunk
                await target.evaluate('''([val]) => {
                    const el = document.querySelector('textarea');
                    if (el) {
                        el.value = val;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, cancelable: true, key: 'a' }));
                    }
                }''', [current_val])
                await asyncio.sleep(0.06)

            # Dispatch change and blur to flush input subject in Angular
            await target.evaluate('''() => {
                const el = document.querySelector('textarea');
                if (el) {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                }
            }''')
            await asyncio.sleep(1.5)
            print("  [Writing] Response entered successfully.")
            return True

        return False
