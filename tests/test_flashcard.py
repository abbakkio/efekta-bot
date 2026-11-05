import pytest
from patchright.async_api import async_playwright
from handlers.flashcard import FlashcardHandler

@pytest.mark.asyncio
async def test_flashcard_handler_can_handle_and_flip(tmp_path):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()

        # Set mock HTML with ef-flashcards-task and 2 cards
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Flashcards</title></head>
        <body>
            <ef-flashcards-task>
                <div class="flashcards-container">
                    <div class="flashcard-list" style="overflow-x: scroll; width: 300px; display: flex;">
                        <ef-flashcard style="min-width: 250px;">
                            <div class="flip-card-inner">
                                <button class="flip-btn">Flip 1</button>
                            </div>
                        </ef-flashcard>
                        <ef-flashcard ef-visibility-observer style="min-width: 250px;">
                            <div class="flip-card-inner">
                                <button class="flip-btn">Flip 2</button>
                            </div>
                        </ef-flashcard>
                    </div>
                </div>
            </ef-flashcards-task>
            <button class="next-task-button mat-mdc-button-disabled" disabled>Next</button>
            <script>
                document.querySelectorAll('.flip-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        btn.closest('.flip-card-inner').classList.add('is-flipped');
                    });
                });
            </script>
        </body>
        </html>
        """
        await page.set_content(html_content)

        handler = FlashcardHandler()
        can = await handler.can_handle(page)
        assert can is True, "FlashcardHandler should detect flashcards"

        acted = await handler.handle(page)
        assert acted is True, "FlashcardHandler should handle flashcards"

        # Check if cards were flipped
        is_flipped_count = await page.locator(".flip-card-inner.is-flipped").count()
        assert is_flipped_count == 2, f"Expected 2 flipped cards, got {is_flipped_count}"

        await browser.close()
