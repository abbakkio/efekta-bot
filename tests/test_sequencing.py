import pytest
from patchright.async_api import async_playwright
from handlers.sequencing import SequencingHandler

def test_sequencing_modal_rules():
    handler = SequencingHandler()

    words1 = ["do", "couldn't", "yoga.", "He"]
    candidates1 = handler._get_candidate_orders(words1)
    assert len(candidates1) > 0
    top1 = candidates1[0]
    assert top1 == ["He", "couldn't", "do", "yoga."]

    words2 = ["relax.", "help", "Yoga", "you", "may"]
    candidates2 = handler._get_candidate_orders(words2)
    assert len(candidates2) > 0
    top2 = candidates2[0]
    assert top2 == ["Yoga", "may", "help", "you", "relax."]

def test_sequencing_prefix_aware_suffix():
    handler = SequencingHandler()
    prefix = ["I", "may"]
    remaining_words = ["be", "not", "to.", "able"]

    candidates = handler._get_candidate_orders(remaining_words, prefix=prefix)
    assert len(candidates) > 0
    top = candidates[0]
    assert top == ["not", "be", "able", "to."]

def test_sequencing_failure_memory():
    handler = SequencingHandler()
    words = ["do", "couldn't", "yoga.", "He"]

    top1 = handler._get_candidate_orders(words)[0]
    handler._failed_permutations.add(tuple(top1))

    candidates_after = handler._get_candidate_orders(words)
    assert tuple(top1) not in [tuple(c) for c in candidates_after]

def test_sequencing_invalid_position_pruning():
    handler = SequencingHandler()
    prefix = ["She"]
    words = ["plans", "hopes", "to", "quit."]

    # Top candidate without invalid positions
    c1 = handler._get_candidate_orders(words, prefix=prefix)
    first_choice = c1[0][0]

    # Mark the first chosen word as INVALID at position 1 (right after prefix 'She')
    handler._invalid_token_positions.add((first_choice, 1))

    c2 = handler._get_candidate_orders(words, prefix=prefix)
    assert len(c2) > 0
    new_first_choice = c2[0][0]
    assert new_first_choice != first_choice, f"Word '{first_choice}' should not be chosen at position 1 after being marked invalid!"

def test_sequencing_task_reset():
    handler = SequencingHandler()
    handler._invalid_token_positions.add(("word", 1))
    handler._failed_permutations.add(("a", "b"))
    handler._current_task_signature = ("a", "b")

    # New task with different words
    handler._check_task_reset(["new", "sentence", "here."])
    assert len(handler._invalid_token_positions) == 0
    assert len(handler._failed_permutations) == 0
    assert handler._current_task_signature == ("here.", "new", "sentence")

@pytest.mark.asyncio
async def test_sequencing_dom_continuous_prefix_gap():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()

        # HTML with:
        # Item 0: is-correct (word: "I")
        # Item 1: is-incorrect (word: "plans") -> GAP
        # Item 2: is-correct (word: "soon.") -> should NOT be locked because of gap!
        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <ef-sequencing-tap-option-task>
                <ol class="ordered-item-container">
                    <li class="is-correct"><span data-qa="markdown-element-container">I</span></li>
                    <li class="is-incorrect"><span data-qa="markdown-element-container">plans</span></li>
                    <li class="is-correct"><span data-qa="markdown-element-container">soon.</span></li>
                </ol>
                <ul class="unordered-item-container">
                    <li><button><span data-qa="markdown-element-container">hope</span></button></li>
                </ul>
            </ef-sequencing-tap-option-task>
            <button class="check-task-button" disabled>Check</button>
        </body>
        </html>
        """
        await page.set_content(html_content)

        state = await page.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.innerText.trim();
                return (b.innerText || '').split('\n')[0].trim();
            };
            const isItemCorrect = (el) => {
                if (!el) return false;
                if (el.classList.contains('is-correct') || el.classList.contains('item-correct')) return true;
                if (el.querySelector('.is-correct, .item-correct, .correct-circle, ef-svg-thumbs-up, [id="thumbs-up"]')) return true;
                return false;
            };

            const items = Array.from(document.querySelectorAll('.ordered-item-container > li'));
            const orderedEls = items.length > 0 ? items : Array.from(document.querySelectorAll('.ordered-item-container ef-sequencing-tap-option-item'));

            const lockedPrefix = [];
            for (let i = 0; i < orderedEls.length; i++) {
                const item = orderedEls[i];
                if (isItemCorrect(item)) {
                    lockedPrefix.push(extractWord(item));
                } else {
                    break;
                }
            }
            return { lockedPrefix };
        }''')

        # Strictly only ["I"] should be locked, NOT ["I", "soon."]!
        assert state["lockedPrefix"] == ["I"], f"Expected lockedPrefix to be ['I'], got {state['lockedPrefix']}"

        await browser.close()

def test_sequencing_large_pool_pruning():
    handler = SequencingHandler()
    words = ['with', 'getting', 'to', 'be', 'well', 'on', 'seem', 'each', 'other.']
    prefix = ['They']

    # Mark 'with' as invalid at position 1 (right after prefix 'They')
    handler._invalid_token_positions.add(('with', 1))

    candidates = handler._get_candidate_orders(words, prefix=prefix)
    assert len(candidates) > 0, "Expected candidate orders to be generated"
    for cand in candidates:
        assert cand[0] != 'with', f"Found candidate with 'with' at slot 1: {prefix + cand}"

@pytest.mark.asyncio
async def test_sequencing_dom_nested_item_no_duplication():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()

        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <ef-sequencing-tap-option-task>
                <ol class="ordered-item-container">
                    <li><ef-sequencing-tap-option-item><span class="item is-correct"><span data-qa="markdown-element-container">They</span></span></ef-sequencing-tap-option-item></li>
                    <li><ef-sequencing-tap-option-item><button class="item is-unassessed"><span data-qa="markdown-element-container">with</span></button></ef-sequencing-tap-option-item></li>
                </ol>
            </ef-sequencing-tap-option-task>
        </body>
        </html>
        """
        await page.set_content(html_content)

        state = await page.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.textContent.trim();
                return (b.textContent || '').split('\n')[0].trim();
            };
            const items = Array.from(document.querySelectorAll('.ordered-item-container > li'));
            const orderedEls = items.length > 0 ? items : Array.from(document.querySelectorAll('.ordered-item-container ef-sequencing-tap-option-item'));
            return orderedEls.map(extractWord);
        }''')

        # Strictly 2 elements, not 4 (no parent + child duplication)!
        assert len(state) == 2, f"Expected 2 ordered elements, got {len(state)}: {state}"
        assert state == ["They", "with"]

        await browser.close()

def test_sequencing_no_reset_when_tokens_move():
    handler = SequencingHandler()
    all_words = ["I", "like", "that", "place,", "busy."]
    handler._check_task_reset(all_words)
    handler._invalid_token_positions.add(("like", 1))

    # Next iteration: some words are now in ordered, but the full set of words is identical
    reordered_words = ["like", "that", "I", "busy.", "place,"]
    handler._check_task_reset(reordered_words)

    # Constraints must NOT be cleared!
    assert ("like", 1) in handler._invalid_token_positions
    assert len(handler._invalid_token_positions) == 1

def test_sequencing_no_punctuation_at_start():
    handler = SequencingHandler()
    words = ["time.", "First", "Yeah,", "that's", "right."]
    candidates = handler._get_candidate_orders(words)
    assert len(candidates) > 0
    top = candidates[0]
    # Starting word cannot end with '.' or '?' or '!'
    assert not top[0].endswith(('.', '?', '!'))
    # Should be capitalized
    assert top[0][0].isupper()

def test_sequencing_single_punctuation_reserved_for_end():
    handler = SequencingHandler()
    prefix = ["We"]
    words = ["hang", "out", "sometimes,", "when", "free."]
    # "free." is the only word ending in '.'
    candidates = handler._get_candidate_orders(words, prefix=prefix)
    assert len(candidates) > 0
    for cand in candidates:
        assert cand[-1] == "free.", f"Expected 'free.' at the end of suffix: {cand}"
        assert cand[0] != "free.", f"'free.' should never be immediate candidate at slot 1: {cand}"

@pytest.mark.asyncio
async def test_sequencing_cdk_drag_detection():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, channel="chrome")
        page = await browser.new_page()

        await page.set_content("""
        <html>
        <body>
            <ef-sequencing-sort-column-task>
                <div class="cdk-drop-list">
                    <ef-sequencing-sort-column-item>
                        <div class="list-item is-correct"><span data-qa="markdown-element-container">A</span></div>
                    </ef-sequencing-sort-column-item>
                    <ef-sequencing-sort-column-item>
                        <div class="cdk-drag list-item"><span data-qa="markdown-element-container">B</span></div>
                    </ef-sequencing-sort-column-item>
                    <ef-sequencing-sort-column-item>
                        <div class="cdk-drag list-item"><span data-qa="markdown-element-container">C</span></div>
                    </ef-sequencing-sort-column-item>
                </div>
            </ef-sequencing-sort-column-task>
            <button class="check-task-button" disabled>Check</button>
        </body>
        </html>
        """)

        handler = SequencingHandler()
        can = await handler.can_handle(page)
        assert can is True

        await browser.close()

def test_sequencing_duplicate_tokens():
    handler = SequencingHandler()
    words = ['great', 'able', 'more.', 'It’d', 'to', 'be', 'be', 'travel', 'lot', 'to', 'a']
    candidates = handler._get_candidate_orders(words)
    assert len(candidates) > 0
    # Every candidate must have all 11 tokens preserved
    for cand in candidates:
        assert len(cand) == len(words), f"Expected length {len(words)}, got {len(cand)}: {cand}"
        assert cand.count('be') == 2
        assert cand.count('to') == 2

    # Top candidate should be the expected grammatical sentence
    top = candidates[0]
    assert top == ['It’d', 'be', 'great', 'to', 'be', 'able', 'to', 'travel', 'a', 'lot', 'more.']

