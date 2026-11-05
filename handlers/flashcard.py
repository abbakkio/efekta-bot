import asyncio
from patchright.async_api import Page, Frame
from .base import BaseHandler

class FlashcardHandler(BaseHandler):
    """Handles flashcard tasks: flips unflipped vocabulary cards and scrolls to the end to trigger visibility observers and unlock Next."""

    async def can_handle(self, target: Page | Frame) -> bool:
        cards = target.locator("ef-flashcard, ef-flashcards-task, .flashcard-list, .flashcards-container")
        if await cards.count() == 0:
            return False

        # Handle if there are any unflipped cards
        has_unflipped = await target.evaluate("""() => {
            const cards = Array.from(document.querySelectorAll('ef-flashcard'));
            return cards.some(c => {
                const inner = c.querySelector('.flip-card-inner');
                return inner && !inner.classList.contains('is-flipped');
            });
        }""")
        return has_unflipped

    async def handle(self, target: Page | Frame) -> bool:
        print("  [Flashcards] Processing vocabulary flashcards...")

        # Flip all unflipped cards
        flipped_count = await target.evaluate("""() => {
            const cards = Array.from(document.querySelectorAll('ef-flashcard'));
            let flipped = 0;
            for (const card of cards) {
                const inner = card.querySelector('.flip-card-inner');
                if (inner && !inner.classList.contains('is-flipped')) {
                    const flipBtn = card.querySelector('.flip-btn') || inner;
                    flipBtn.click();
                    flipped++;
                }
            }
            return flipped;
        }""")

        if flipped_count > 0:
            print(f"  [Flashcards] Flipped {flipped_count} cards.")
            await asyncio.sleep(0.5)

        # Scroll container and last card into view so [ef-visibility-observer] fires
        scrolled = await target.evaluate("""() => {
            const list = document.querySelector('.flashcard-list, .flashcards-container');
            const lastCard = document.querySelector('ef-flashcard[ef-visibility-observer], ef-flashcard:last-child');
            if (lastCard) {
                lastCard.scrollIntoView({ behavior: 'smooth', inline: 'end', block: 'nearest' });
            }
            if (list && list.scrollWidth > list.clientWidth) {
                list.scrollLeft = list.scrollWidth;
                list.dispatchEvent(new Event('scroll'));
                return true;
            }
            return !!lastCard;
        }""")

        if scrolled:
            print("  [Flashcards] Scrolled card container to end.")
            await asyncio.sleep(1.0)

        await self.sleep_delay(0.5, 1.0)
        return True
