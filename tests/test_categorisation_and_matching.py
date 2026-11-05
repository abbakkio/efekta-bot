import pytest
from patchright.async_api import async_playwright
from handlers.categorisation import CategorisationHandler
from handlers.matching import MatchingHandler

HTML_CATEGORISATION = """
<html>
<body>
    <ef-categorisation-task>
        <button class="item target" aria-label="Music - category">Music</button>
        <button class="item target" aria-label="Places - category">Places</button>
        <button class="item target" aria-label="People - category">People</button>
        
        <button class="item option" aria-label="artist - option">artist</button>
        <button class="item option" aria-label="hall - option">hall</button>
        <button class="item option" aria-label="guitar - option">guitar</button>
    </ef-categorisation-task>
</body>
</html>
"""

HTML_MATCHING = """
<html>
<body>
    <ef-matching-task>
        <ef-matching-option>
            <div role="button">
                <img alt="A person wearing headphones and using turntables as a DJ." />
            </div>
        </ef-matching-option>
        <ef-matching-option>
            <div role="button">
                <span>DJ (disc jockey)</span>
            </div>
        </ef-matching-option>
    </ef-matching-task>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_categorisation_handler():
    handler = CategorisationHandler()
    assert handler._match_category("artist", ["Music", "Places", "People"]) == "People"
    assert handler._match_category("hall", ["Music", "Places", "People"]) == "Places"
    assert handler._match_category("guitar", ["Music", "Places", "People"]) == "Music"

@pytest.mark.asyncio
async def test_matching_handler(tmp_path):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page()
        await page.set_content(HTML_MATCHING)
        
        handler = MatchingHandler()
        assert await handler.can_handle(page) is True
        handled = await handler.handle(page)
        assert handled is True
        
        await browser.close()
