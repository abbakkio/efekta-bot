import asyncio
import itertools
from patchright.async_api import Page, Frame
from .base import BaseHandler

MODALS = {
    "may", "might", "could", "couldn't", "can", "can't", "must", "mustn't",
    "should", "shouldn't", "will", "won't", "would", "wouldn't"
}
NEGATIVES = {
    "not", "doesn't", "don't", "didn't", "haven't", "hasn't", "hadn't",
    "can't", "couldn't", "won't", "wouldn't", "shouldn't", "mustn't",
    "isn't", "aren't", "wasn't", "weren't"
}
PRONOUNS = {
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"
}
PREPOSITIONS = {
    "to", "in", "at", "on", "with", "for", "from", "about", "of", "into", "onto", "by"
}
ARTICLES = {"a", "an", "the"}
AUXILIARIES = {
    "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did"
}

def score_pair(w1: str, w2: str) -> int:
    w1_clean = w1.rstrip(".?!,").lower()
    w2_clean = w2.rstrip(".?!,").lower()

    score = 0
    # Pronoun + Auxiliary / Modals
    if w1_clean in {"i"} and w2_clean in {"am", "was", "have", "had", "will", "would", "can", "could", "'m", "'ve", "'d", "'ll"}:
        score += 55
    elif w1_clean in {"he", "she", "it"} and w2_clean in {"is", "was", "has", "had", "will", "would", "can", "could", "'s"}:
        score += 55
    elif w1_clean in {"we", "they", "you"} and w2_clean in {"are", "were", "have", "had", "will", "would", "can", "could", "'re"}:
        score += 55

    # Subject pronoun + 3rd person singular verb (e.g. She hopes, He plans, She wants)
    if w1_clean in {"he", "she", "it"} and (w2_clean.endswith("s") or w2_clean.endswith("es")) and w2_clean not in {"is", "was", "has"}:
        score += 50
    elif w1_clean in {"i", "we", "they", "you"} and w2_clean in {"hope", "plan", "want", "intend", "think", "believe", "decide", "like", "need"}:
        score += 50

    # Auxiliary + -ing verb (e.g. am looking, is planning, was hoping)
    if w1_clean in {"am", "is", "are", "was", "were"} and w2_clean.endswith("ing"):
        score += 50

    # Verbal expressions + "to" (looking to, planning to, intend to, decided to, want to, etc.)
    if w1_clean in {"looking", "planning", "going", "hoping", "trying", "hope", "hopes", "plan", "plans", "want", "wants", "wanted", "intend", "intends", "intended", "decide", "decides", "decided", "like", "likes", "need", "needs", "needed", "able", "expected"} and w2_clean == "to":
        score += 60

    # "to" + infinitive base verb (to increase, to improve, to move, to leave, etc.)
    if w1_clean == "to" and w2_clean in {"increase", "improve", "learn", "change", "make", "get", "take", "find", "apply", "start", "become", "continue", "develop", "lose", "do", "go", "eat", "be", "work", "relax", "exercise", "see", "help", "travel", "study", "move", "leave", "stay", "join", "accept", "quit", "retire", "buy", "sell", "live"}:
        score += 60

    # Verb + preposition (move into, apply for, look at, etc.)
    if w1_clean in {"move", "moved"} and w2_clean == "into":
        score += 50
    elif w1_clean in PREPOSITIONS and w2_clean not in PREPOSITIONS and w2_clean not in MODALS:
        score += 20

    # Transitive verb + possessive (increase my, change your, improve our, etc.)
    if w2_clean in {"my", "your", "his", "her", "our", "their"}:
        score += 35

    # Possessive + noun (my proficiency, my job, my career, my life, etc.)
    if w1_clean in {"my", "your", "his", "her", "our", "their"}:
        score += 45

    if (w1_clean in PRONOUNS or w1[0].isupper()) and w2_clean in NEGATIVES:
        score += 30
    elif (w1_clean in PRONOUNS or w1[0].isupper()) and w2_clean in MODALS:
        score += 25
    elif w1_clean in NEGATIVES and w2_clean in {"have", "has", "be", "do", "need", "go", "eat", "get", "feel", "lose"}:
        score += 30
    elif w1_clean == "have" and w2_clean.startswith("to"):
        score += 28
    elif w1_clean == "ought" and w2_clean.startswith("to"):
        score += 28
    elif w1_clean == "had" and w2_clean == "better":
        score += 28
    elif w1_clean == "better" and w2_clean not in MODALS and w2_clean not in PREPOSITIONS:
        score += 22
    elif w1_clean in MODALS and w2_clean not in MODALS and w2_clean not in PRONOUNS and w2_clean not in PREPOSITIONS:
        score += 20
    elif (w1_clean in PRONOUNS or w1[0].isupper()) and w2_clean not in MODALS and w2_clean not in PREPOSITIONS and w2_clean not in ARTICLES:
        score += 12
    elif w1_clean not in MODALS and w1_clean not in PRONOUNS and w2_clean in PRONOUNS:
        score += 10
    elif w1_clean in PREPOSITIONS and (w2_clean in ARTICLES or w2_clean in PRONOUNS or w2_clean not in MODALS):
        score += 10
    elif w1_clean in ARTICLES and w2_clean not in PREPOSITIONS and w2_clean not in MODALS:
        score += 10
    elif w1_clean in AUXILIARIES and w2_clean not in AUXILIARIES and w2_clean not in MODALS:
        score += 8

    return score

class SequencingHandler(BaseHandler):
    """Handles Efekta sequencing tasks (ef-sequencing-tap-option-task, ordering word tokens, and CDK drag column tasks)."""

    def __init__(self):
        super().__init__()
        self._failed_permutations = set()

    async def can_handle(self, target: Page | Frame) -> bool:
        next_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next"), '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Continue")'
        ).first
        if await next_btn.count() > 0:
            return False

        task = target.locator('ef-sequencing-tap-option-task:visible, ef-sequencing-task:visible, ef-sequencing-sort-column-task:visible')
        if await task.count() > 0:
            return True

        unordered = target.locator('.unordered-item-container button:visible')
        ordered = target.locator('.ordered-item-container button:visible')
        if (await unordered.count() > 0) or (await ordered.count() > 0):
            return True

        sort_column = target.locator('ef-sequencing-sort-column-task .cdk-drag:visible')
        if await sort_column.count() > 0:
            return True

        return False

    def _score_sentence(self, seq: list[str]) -> int:
        total = 0
        if len(seq) > 1:
            w1_start = seq[0].rstrip(".?!,").lower()
            w2_start = seq[1].rstrip(".?!,").lower()
            if w2_start in NEGATIVES and (w1_start in PRONOUNS or seq[0][0].isupper()):
                total += 80
            elif w2_start in MODALS and (w1_start in PRONOUNS or seq[0][0].isupper()):
                total += 60

        for i in range(len(seq) - 1):
            w1 = seq[i]
            w2 = seq[i+1]
            w1_clean = w1.rstrip(".?!,").lower()
            w2_clean = w2.rstrip(".?!,").lower()

            if (w1_clean in PRONOUNS or w1[0].isupper()) and w2_clean in NEGATIVES:
                total += 65
            elif w1_clean in NEGATIVES and w2_clean in {"have", "has", "be", "do", "need", "go", "eat", "get", "feel", "lose"}:
                total += 60
            elif w1_clean == "have" and w2_clean.startswith("to"):
                total += 55
            elif w1_clean == "ought" and w2_clean.startswith("to"):
                total += 55
            elif w1_clean == "had" and w2_clean == "better":
                total += 55
            elif w1_clean == "to" and w2_clean in {"lose", "do", "go", "eat", "be", "work", "relax", "exercise", "take", "see", "help", "feel"}:
                total += 50
            elif w1_clean in MODALS and w2_clean == "not":
                total += 45
            elif w1_clean == "not" and w2_clean in {"be", "do", "have", "go", "help", "relax", "feel", "think", "run", "eat"}:
                total += 35
            elif w1_clean == "be" and w2_clean == "able":
                total += 30
            elif w1_clean == "able" and w2_clean.startswith("to"):
                total += 30
            elif w1_clean in MODALS and w2_clean not in MODALS and w2_clean not in PRONOUNS and w2_clean not in PREPOSITIONS:
                total += 35
            elif w1_clean in {"lose", "do", "take", "eat", "drink", "play"} and w2_clean in {"weight", "yoga", "advice", "sports", "water", "food"}:
                total += 40
            elif w1_clean not in MODALS and w1_clean not in PRONOUNS and w2_clean in PRONOUNS:
                total += 25
            elif w1_clean in PRONOUNS and i > 1 and w2_clean not in MODALS and w2_clean not in PREPOSITIONS:
                total += 15
            else:
                total += score_pair(w1, w2)

        return total

    def _get_candidate_orders(self, words: list[str], prefix: list[str] = None) -> list[list[str]]:
        if not words:
            return []

        prefix = prefix or []
        end_candidates = [w for w in words if w.endswith(('.', '?', '!'))]
        end = end_candidates[0] if end_candidates else None

        start_candidates = [w for w in words if w[0].isupper() and not w.endswith(('.', '?', '!'))] if not prefix else []
        start = start_candidates[0] if start_candidates else None

        mid_copy = list(words)
        if start and start in mid_copy:
            mid_copy.remove(start)
        if end and end in mid_copy:
            mid_copy.remove(end)

        middle = mid_copy
        perms = list(itertools.permutations(middle))

        def score_candidate(perm):
            suffix = ([start] if start else []) + list(perm) + ([end] if end else [])
            full_seq = prefix + suffix
            return self._score_sentence(full_seq)

        perms.sort(key=score_candidate, reverse=True)
        candidates = [([start] if start else []) + list(p) + ([end] if end else []) for p in perms]

        valid = [c for c in candidates if tuple(prefix + c) not in self._failed_permutations]
        return valid if valid else candidates

    async def _handle_cdk_drag(self, target: Page | Frame) -> bool:
        """Handles Angular CDK Drag and Drop column sequencing tasks."""
        page = target.page if isinstance(target, Frame) else target
        check_btn = target.locator('button.check-task-button:not([disabled]):visible').first
        if await check_btn.count() > 0:
            print("  [Sequencing] Check button is enabled. Submitting sequence...")
            await self.sleep_delay(0.5, 0.8)
            await check_btn.click()
            await asyncio.sleep(2.0)
            return True

        drag_items = target.locator('.cdk-drag:visible')
        count = await drag_items.count()
        if count <= 1:
            return False

        # Pick up item 0 and move it to bottom, or adjust order
        print(f"  [Sequencing] Reordering CDK drag items (count: {count}) via keyboard...")
        first_item = drag_items.first
        await first_item.click()
        await asyncio.sleep(0.3)
        await page.keyboard.press("Space")
        await asyncio.sleep(0.3)
        await page.keyboard.press("ArrowDown")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Space")
        await asyncio.sleep(1.0)

        # Now click Check if enabled
        if await check_btn.count() > 0:
            print("  [Sequencing] Submitting sequence...")
            await check_btn.click()
            await asyncio.sleep(2.0)
        return True

    async def handle(self, target: Page | Frame) -> bool:
        # Check if CDK Drag and Drop column sorting is active (ef-sequencing-sort-column-task)
        sort_column = target.locator('ef-sequencing-sort-column-task:visible')
        tap_task = target.locator('ef-sequencing-tap-option-task:visible, .unordered-item-container:visible')
        if await sort_column.count() > 0 and await tap_task.count() == 0:
            return await self._handle_cdk_drag(target)

        check_btn = target.locator('button.check-task-button:visible').first

        # 1. Inspect active state of ordered and unordered containers
        state = await target.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.innerText.trim();
                return (b.innerText || '').split('\n')[0].trim();
            };
            const lockedPrefix = Array.from(document.querySelectorAll('.ordered-item-container .item.is-correct'))
                .map(extractWord);
            const unassessedOrdered = Array.from(document.querySelectorAll('.ordered-item-container button'))
                .map(extractWord);
            const unorderedWords = Array.from(document.querySelectorAll('.unordered-item-container button'))
                .map(extractWord).filter(Boolean);
            const checkEnabled = document.querySelector('button.check-task-button') && !document.querySelector('button.check-task-button').disabled;
            return {
                lockedPrefix,
                unassessedOrdered,
                unorderedWords,
                checkEnabled
            };
        }''')

        locked_prefix = state['lockedPrefix']
        unassessed_ordered = state['unassessedOrdered']
        unordered_words = state['unorderedWords']
        check_enabled = state['checkEnabled']

        # 2. If all items are ordered and Check button is enabled, click Check
        if not unordered_words and check_enabled:
            current_full = locked_prefix + unassessed_ordered
            print(f"  [Sequencing] Submitting sequence: {' '.join(current_full)}...")
            await self.sleep_delay(0.4, 0.7)
            await check_btn.click()
            await asyncio.sleep(2.0)

            next_btn = target.locator('button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next")').first
            if await next_btn.count() > 0:
                print("  [Sequencing] Sequence accepted! Next is enabled.")
                self._failed_permutations.clear()
                return True
            else:
                print(f"  [Sequencing] Sequence rejected. Recording failure: {tuple(current_full)}")
                self._failed_permutations.add(tuple(current_full))
                while True:
                    ret = await target.evaluate('''() => {
                        const b = document.querySelector('.ordered-item-container button');
                        if (b) { b.click(); return true; }
                        return false;
                    }''')
                    if not ret:
                        break
                    await asyncio.sleep(0.3)
                return True

        # 3. If there are unassessed buttons in ordered container while unordered pool is not empty, reset them
        if unassessed_ordered and unordered_words:
            print("  [Sequencing] Resetting unassessed ordered tokens to pool...")
            while True:
                ret = await target.evaluate('''() => {
                    const b = document.querySelector('.ordered-item-container button');
                    if (b) { b.click(); return true; }
                    return false;
                }''')
                if not ret:
                    break
                await asyncio.sleep(0.3)
            await asyncio.sleep(0.4)

        # 4. Re-collect unordered words after reset
        pool_words = await target.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.innerText.trim();
                return (b.innerText || '').split('\n')[0].trim();
            };
            return Array.from(document.querySelectorAll('.unordered-item-container button'))
                .map(extractWord).filter(Boolean);
        }''')

        if not pool_words:
            if check_enabled and await check_btn.count() > 0:
                print("  [Sequencing] Clicking 'Check'...")
                await check_btn.click()
                await asyncio.sleep(1.8)
                return True
            return False

        candidates = self._get_candidate_orders(pool_words, prefix=locked_prefix)
        if not candidates:
            return False

        chosen_suffix = candidates[0]
        full_display = locked_prefix + chosen_suffix
        print(f"  [Sequencing] Ordering tokens: {' '.join(full_display)}...")

        # 5. Tap words into the ordered container in chosen order
        for word in chosen_suffix:
            tapped = await target.evaluate(r'''(targetWord) => {
                const extractWord = (b) => {
                    if (!b) return '';
                    const el = b.querySelector('[data-qa="markdown-element-container"]');
                    if (el) return el.innerText.trim();
                    return (b.innerText || '').split('\n')[0].trim();
                };
                const btns = Array.from(document.querySelectorAll('.unordered-item-container button'));
                for (const b of btns) {
                    if (extractWord(b) === targetWord) {
                        b.click();
                        return true;
                    }
                }
                return false;
            }''', word)
            if tapped:
                await asyncio.sleep(0.4)

        await asyncio.sleep(0.6)

        # 6. Click Check if enabled
        if await check_btn.count() > 0 and not await check_btn.is_disabled():
            print("  [Sequencing] Clicking 'Check'...")
            await check_btn.click()
            await asyncio.sleep(2.0)

            next_btn = target.locator('button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next")').first
            if await next_btn.count() > 0:
                print("  [Sequencing] Sequence accepted! Next is enabled.")
                self._failed_permutations.clear()
            else:
                failed_tuple = tuple(full_display)
                print(f"  [Sequencing] Sequence rejected. Recording failure: {failed_tuple}")
                self._failed_permutations.add(failed_tuple)
                while True:
                    ret = await target.evaluate('''() => {
                        const b = document.querySelector('.ordered-item-container button');
                        if (b) { b.click(); return true; }
                        return false;
                    }''')
                    if not ret:
                        break
                    await asyncio.sleep(0.3)

        return True
