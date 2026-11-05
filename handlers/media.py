import asyncio
from patchright.async_api import Page, Frame
from .base import BaseHandler

class MediaPlaybackHandler(BaseHandler):
    """Handles audio and video elements, accelerating playback and waiting for completion."""

    async def can_handle(self, target: Page | Frame) -> bool:
        # 1. If Next or Continue is already enabled, let NavigationHandler advance
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

        # 2. If an informational dialog is covering the screen, let NavigationHandler dismiss it first
        dialog = target.locator(
            'button:not([disabled]):visible:has-text("Okay, got it"), '
            'button:not([disabled]):visible:has-text("Got it"), '
            'button:not([disabled]):visible:has-text("I understand")'
        ).first
        if await dialog.count() > 0:
            return False

        # 3. If interactive exercise elements (choices, gaps, recorder) are visible, let them handle it first
        interactive = target.locator(
            'button[role="radio"]:visible, div[role="radio"]:visible, '
            '.option-button:visible, .selection-gap-button:visible, '
            'button[data-qa="audio-record-or-play"]:visible, '
            'button.audio-recorder-btn:visible, '
            'ef-multiple-choice-speech-task:visible, '
            'ef-multiple-choice-speech-task-response-option:visible'
        )
        if await interactive.count() > 0:
            return False

        audio = target.locator("audio, video").first
        if await audio.count() > 0:
            is_ended = await audio.evaluate("el => el.ended")
            return not is_ended
        return False

    async def handle(self, target: Page | Frame) -> bool:
        audio = target.locator("audio, video").first
        if await audio.count() == 0:
            return False

        is_ended = await audio.evaluate("el => el.ended")
        if is_ended:
            return False

        print("  [Media] Accelerating media playback...")
        try:
            await audio.evaluate("el => { el.playbackRate = 4.0; el.play().catch(() => {}); }")
        except Exception:
            pass

        # Wait while media is playing or until interactive elements / advance button appear
        for _ in range(15):
            await asyncio.sleep(0.5)
            # Check if Next button got enabled
            next_enabled = await target.locator(
                'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
                'button[class*="main-next"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
                'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next")'
            ).count() > 0
            if next_enabled:
                print("  [Media] Next button unlocked during playback.")
                break

            # Check if interactive prompt reached
            interactive = await target.locator(
                'button[role="radio"]:visible, .option-button:visible, '
                'button[data-qa="audio-record-or-play"]:visible, '
                'ef-multiple-choice-speech-task:visible'
            ).count() > 0
            if interactive:
                print("  [Media] Interactive prompt reached during playback.")
                break

            is_ended = await audio.evaluate("el => el.ended")
            if is_ended:
                print("  [Media] Media finished playing.")
                break

        await self.sleep_delay(0.5, 1.0)
        return True
