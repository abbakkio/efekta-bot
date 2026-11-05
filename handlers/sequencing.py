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
    elif w1_clean in {"i", "we", "they", "you"} and w2_clean in {"hope", "plan", "want", "intend", "think", "believe", "decide", "like", "need", "seem", "appear", "look", "sound", "feel", "know", "mean", "tend"}:
        score += 50

    # Auxiliary + -ing verb (e.g. am looking, is planning, was hoping, be getting)
    if w1_clean in {"am", "is", "are", "was", "were", "be", "been"} and w2_clean.endswith("ing"):
        score += 50

    # Verbal expressions + "to" (looking to, planning to, intend to, decided to, want to, seem to, etc.)
    if w1_clean in {"looking", "planning", "going", "hoping", "trying", "hope", "hopes", "plan", "plans", "want", "wants", "wanted", "intend", "intends", "intended", "decide", "decides", "decided", "like", "likes", "need", "needs", "needed", "able", "expected", "seem", "seems", "seemed", "appear", "appears", "appeared", "tend", "tends", "claim", "claims", "happen", "happens"} and w2_clean == "to":
        score += 60

    # "to" + infinitive base verb (to increase, to improve, to move, to leave, etc.)
    if w1_clean == "to" and w2_clean in {"increase", "improve", "learn", "change", "make", "get", "take", "find", "apply", "start", "become", "continue", "develop", "lose", "do", "go", "eat", "be", "work", "relax", "exercise", "see", "help", "travel", "study", "move", "leave", "stay", "join", "accept", "quit", "retire", "buy", "sell", "live"}:
        score += 60

    # Phrasal verbs and collocations (getting on, each other, well with, etc.)
    if w1_clean in {"get", "gets", "getting", "got"} and w2_clean in {"on", "in", "up", "along", "with", "out", "off", "back", "away", "over", "through", "together"}:
        score += 55
    elif w1_clean == "on" and w2_clean in {"well", "badly", "time"}:
        score += 45
    elif w1_clean == "well" and w2_clean in {"with", "at", "for"}:
        score += 45
    elif w1_clean == "each" and w2_clean.startswith("other"):
        score += 60
    elif w1_clean == "one" and w2_clean.startswith("another"):
        score += 60
    elif w1_clean == "with" and w2_clean in {"each", "one", "all", "them", "us", "him", "her", "me", "you"}:
        score += 45

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
        self._invalid_token_positions = set()  # set of (word, absolute_position_index)
        self._current_task_signature = None
        self._assign_index_failed_positions = set()  # set of (item_idx, pos)
        self._assign_index_task_id = None
        self._cdk_drag_failed_permutations = set()
        self._cdk_drag_invalid_positions = set()  # set of (text, position_idx)
        self._cdk_drag_task_id = None

    def _check_task_reset(self, all_words: list[str]):
        """Resets failed permutations and position constraints when a new task is detected."""
        if not all_words:
            return
        sig = tuple(sorted(all_words))
        if self._current_task_signature is None:
            self._current_task_signature = sig
        elif self._current_task_signature != sig:
            print(f"  [Sequencing] New task detected (words changed). Resetting memory.")
            self._current_task_signature = sig
            self._failed_permutations.clear()
            self._invalid_token_positions.clear()

    async def can_handle(self, target: Page | Frame) -> bool:
        next_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next"), '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Continue")'
        ).first
        if await next_btn.count() > 0:
            return False

        task = target.locator('ef-sequencing-tap-option-task:visible, ef-sequencing-task:visible, ef-sequencing-sort-column-task:visible, ef-sequencing-assign-index-task:visible')
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
        p_len = len(prefix)
        total_len = p_len + len(words)

        # Check if there is strictly one punctuation-ending word that should be reserved for the end
        end_candidates = [w for w in words if w.endswith(('.', '?', '!'))]
        reserved_end = None
        if len(end_candidates) == 1 and not any(p.endswith(('.', '?', '!')) for p in prefix) and len(words) > 1:
            if (end_candidates[0], total_len - 1) not in self._invalid_token_positions:
                reserved_end = end_candidates[0]

        # The pool of candidate tokens available for the immediate slot (next_slot = p_len)
        pool_for_next = [w for w in words if w != reserved_end] if reserved_end else list(words)
        if not pool_for_next and reserved_end:
            pool_for_next = [reserved_end]

        # STRICT DEDUCTIVE PRUNING FOR IMMEDIATE SLOT:
        # A word is only eligible for next_slot if it has NEVER failed at next_slot
        valid_next_words = [
            w for w in pool_for_next
            if (w, p_len) not in self._invalid_token_positions
            and not (p_len == 0 and total_len > 1 and w.endswith(('.', '?', '!')))
        ]
        if not valid_next_words:
            # Fallback only if every eligible word was pruned
            valid_next_words = [
                w for w in pool_for_next
                if not (p_len == 0 and total_len > 1 and w.endswith(('.', '?', '!')))
            ] or list(pool_for_next)

        # Sort valid_next_words by linguistic likelihood
        if p_len == 0:
            valid_next_words.sort(
                key=lambda w: (
                    1 if (w[0].isupper() and not w.endswith(('.', '?', '!'))) else (0.5 if w[0].isupper() else 0),
                    self._score_sentence([w])
                ),
                reverse=True
            )
        else:
            prev_word = prefix[-1]
            valid_next_words.sort(
                key=lambda w: (
                    score_pair(prev_word, w),
                    self._score_sentence(prefix + [w])
                ),
                reverse=True
            )

        candidates = []
        for next_word in valid_next_words:
            rest = [w for w in words if w != next_word]
            if reserved_end and reserved_end in rest:
                rest.remove(reserved_end)

            if len(rest) <= 6:
                r_perms = list(itertools.permutations(rest))
            elif len(rest) == 7:
                r_perms = list(itertools.islice(itertools.permutations(rest), 1000))
            else:
                perms = []
                for r_cand in rest:
                    rem = [w for w in rest if w != r_cand]
                    chain = [r_cand]
                    curr = r_cand
                    while rem:
                        best_next = max(rem, key=lambda w: score_pair(curr, w))
                        chain.append(best_next)
                        rem.remove(best_next)
                        curr = best_next
                    perms.append(tuple(chain))
                r_perms = perms

            for r_p in r_perms:
                suffix = [next_word] + list(r_p) + ([reserved_end] if reserved_end else [])
                full = tuple(prefix + suffix)
                if full in self._failed_permutations:
                    continue

                # Check position constraints for subsequent tokens
                violates = False
                for j, w in enumerate(suffix):
                    abs_pos = p_len + j
                    if (w, abs_pos) in self._invalid_token_positions:
                        violates = True
                        break
                if not violates:
                    candidates.append(suffix)

        # Relax deeper position constraints if all candidates were pruned,
        # but NEVER relax the immediate next slot or non-failed full sequence
        if not candidates:
            for next_word in valid_next_words:
                rest = [w for w in words if w != next_word]
                if reserved_end and reserved_end in rest:
                    rest.remove(reserved_end)
                chain = [next_word]
                rem = list(rest)
                curr = next_word
                while rem:
                    best_next = max(rem, key=lambda w: score_pair(curr, w))
                    chain.append(best_next)
                    rem.remove(best_next)
                    curr = best_next
                suffix = chain + ([reserved_end] if reserved_end else [])
                if tuple(prefix + suffix) not in self._failed_permutations:
                    candidates.append(suffix)

        def score_candidate(suffix):
            return self._score_sentence(prefix + suffix)

        candidates.sort(key=score_candidate, reverse=True)
        return candidates

    async def _handle_cdk_drag(self, target: Page | Frame) -> bool:
        """Handles Angular CDK Drag and Drop column sequencing tasks."""
        page = target.page if isinstance(target, Frame) else target

        # Check if already completed (Next button enabled)
        next_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next")'
        ).first
        if await next_btn.count() > 0:
            self._cdk_drag_failed_permutations.clear()
            self._cdk_drag_invalid_positions.clear()
            return False

        # 1. Read all sort-column items
        items = await target.evaluate(r'''() => {
            const els = Array.from(document.querySelectorAll("ef-sequencing-sort-column-item"));
            return els.map((el, i) => {
                const textEl = el.querySelector('[data-qa="markdown-element-container"]');
                const text = textEl ? textEl.innerText.trim() : (el.innerText || '').split('\n')[0].trim();
                const isCorrect = el.classList.contains('is-correct') || !!el.querySelector('.is-correct, ef-svg-thumbs-up');
                const isIncorrect = el.classList.contains('is-incorrect') || !!el.querySelector('.is-incorrect, ef-svg-thumbs-down');
                const isDraggable = !!el.querySelector('.cdk-drag') || el.classList.contains('cdk-drag');
                return { i, text, isCorrect, isIncorrect, isDraggable };
            });
        }''')

        if not items:
            return False

        # Reset state if task changed
        task_sig = tuple(sorted([it['text'] for it in items]))
        if self._cdk_drag_task_id != task_sig:
            self._cdk_drag_task_id = task_sig
            self._cdk_drag_failed_permutations.clear()
            self._cdk_drag_invalid_positions.clear()

        # Record invalid positions from current assessment
        for it in items:
            if it['isIncorrect']:
                self._cdk_drag_invalid_positions.add((it['text'], it['i']))

        # Check button locator
        check_btn = target.locator('button.check-task-button:not([disabled]):not(.mat-mdc-button-disabled):visible').first

        # If all items are correct, click check or next
        if all(it['isCorrect'] for it in items):
            if await check_btn.count() > 0:
                await check_btn.click()
                await asyncio.sleep(1.5)
            return True

        # Unlocked items that can be reordered
        unlocked_items = [it for it in items if not it['isCorrect'] and it['isDraggable']]
        if not unlocked_items:
            if await check_btn.count() > 0:
                await check_btn.click()
                await asyncio.sleep(1.5)
                return True
            return False

        unlocked_indices = [it['i'] for it in unlocked_items]
        unlocked_texts = [it['text'] for it in unlocked_items]

        # Current full order
        current_full = tuple([it['text'] for it in items])

        # If Check button is ALREADY enabled and current_full has not failed yet, submit it
        if await check_btn.count() > 0 and current_full not in self._cdk_drag_failed_permutations:
            print(f"  [Sequencing] Submitting CDK column sequence: {current_full}...")
            self._cdk_drag_failed_permutations.add(current_full)
            await check_btn.click()
            await asyncio.sleep(1.5)

            # Read feedback immediately
            res = await target.evaluate(r'''() => {
                const els = Array.from(document.querySelectorAll("ef-sequencing-sort-column-item"));
                return els.map((el, i) => {
                    const textEl = el.querySelector('[data-qa="markdown-element-container"]');
                    const text = textEl ? textEl.innerText.trim() : (el.innerText || '').split('\n')[0].trim();
                    const isIncorrect = el.classList.contains('is-incorrect') || !!el.querySelector('.is-incorrect, ef-svg-thumbs-down');
                    return { i, text, isIncorrect };
                });
            }''')
            for r in res:
                if r['isIncorrect']:
                    self._cdk_drag_invalid_positions.add((r['text'], r['i']))
            return True

        # Find best permutation of unlocked texts
        valid_perms = []
        for perm in itertools.permutations(unlocked_texts):
            full_cand = list([it['text'] for it in items])
            for u_idx, text in zip(unlocked_indices, perm):
                full_cand[u_idx] = text
            full_cand = tuple(full_cand)
            if full_cand in self._cdk_drag_failed_permutations:
                continue
            if any((perm[j], unlocked_indices[j]) in self._cdk_drag_invalid_positions for j in range(len(perm))):
                continue
            valid_perms.append(perm)

        chosen_perm = valid_perms[0] if valid_perms else (
            [p for p in itertools.permutations(unlocked_texts) if tuple(
                [p[unlocked_indices.index(it['i'])] if it['i'] in unlocked_indices else it['text'] for it in items]
            ) not in self._cdk_drag_failed_permutations] or list(itertools.permutations(unlocked_texts))
        )[0]

        # Reorder draggable items to match chosen_perm
        drags_info = await target.evaluate(r'''() => {
            return Array.from(document.querySelectorAll(".cdk-drag")).map((el, i) => {
                const r = el.getBoundingClientRect();
                const textEl = el.querySelector('[data-qa="markdown-element-container"]');
                const text = textEl ? textEl.innerText.trim() : (el.innerText || '').split('\n')[0].trim();
                return {
                    i,
                    text,
                    rect: { x: r.x, y: r.y, w: r.width, h: r.height }
                };
            });
        }''')

        if len(drags_info) >= 2:
            frame_offset_x = 0
            frame_offset_y = 0
            if isinstance(target, Frame):
                frame_box = await page.locator("iframe").first.bounding_box()
                if frame_box:
                    frame_offset_x = frame_box["x"]
                    frame_offset_y = frame_box["y"]

            curr_drag_texts = [d['text'] for d in drags_info]
            target_drag_texts = list(chosen_perm)

            # Move elements that are out of order
            for target_idx, target_text in enumerate(target_drag_texts):
                if target_text not in curr_drag_texts:
                    continue
                current_idx = curr_drag_texts.index(target_text)
                if current_idx != target_idx:
                    src_d = drags_info[current_idx]
                    dst_d = drags_info[target_idx]

                    src_x = frame_offset_x + src_d["rect"]["x"] + src_d["rect"]["w"] / 2
                    src_y = frame_offset_y + src_d["rect"]["y"] + src_d["rect"]["h"] / 2

                    dst_x = frame_offset_x + dst_d["rect"]["x"] + dst_d["rect"]["w"] / 2
                    if target_idx < current_idx:
                        dst_y = frame_offset_y + dst_d["rect"]["y"] - 15
                    else:
                        dst_y = frame_offset_y + dst_d["rect"]["y"] + dst_d["rect"]["h"] + 15

                    print(f"  [Sequencing] Dragging '{target_text}' from position {current_idx} to {target_idx}...")
                    await page.mouse.move(src_x, src_y)
                    await page.mouse.down()
                    await asyncio.sleep(0.15)
                    steps = 20
                    for s in range(1, steps + 1):
                        curr_x = src_x + (dst_x - src_x) * (s / steps)
                        curr_y = src_y + (dst_y - src_y) * (s / steps)
                        await page.mouse.move(curr_x, curr_y)
                        await asyncio.sleep(0.015)
                    await asyncio.sleep(0.2)
                    await page.mouse.up()
                    await asyncio.sleep(1.0)
                    break

        # Submit if Check button is enabled
        check_btn = target.locator('button.check-task-button:not([disabled]):not(.mat-mdc-button-disabled):visible').first
        if await check_btn.count() > 0:
            new_items = await target.evaluate(r'''() => {
                const els = Array.from(document.querySelectorAll("ef-sequencing-sort-column-item"));
                return els.map(el => {
                    const textEl = el.querySelector('[data-qa="markdown-element-container"]');
                    return textEl ? textEl.innerText.trim() : (el.innerText || '').split('\n')[0].trim();
                });
            }''')
            full_perm = tuple(new_items)
            print(f"  [Sequencing] Submitting sequence: {full_perm}...")
            self._cdk_drag_failed_permutations.add(full_perm)
            await check_btn.click()
            await asyncio.sleep(1.5)

            # Read feedback
            res = await target.evaluate(r'''() => {
                const els = Array.from(document.querySelectorAll("ef-sequencing-sort-column-item"));
                return els.map((el, i) => {
                    const textEl = el.querySelector('[data-qa="markdown-element-container"]');
                    const text = textEl ? textEl.innerText.trim() : (el.innerText || '').split('\n')[0].trim();
                    const isIncorrect = el.classList.contains('is-incorrect') || !!el.querySelector('.is-incorrect, ef-svg-thumbs-down');
                    return { i, text, isIncorrect };
                });
            }''')
            for r in res:
                if r['isIncorrect']:
                    self._cdk_drag_invalid_positions.add((r['text'], r['i']))
            return True

        return True

    async def _handle_assign_index(self, target: Page | Frame) -> bool:
        """Handles ef-sequencing-assign-index-task (ordering items/images by assigning index positions 1..N via drawer)."""
        next_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next")'
        ).first
        if await next_btn.count() > 0:
            return False

        task_el = target.locator('ef-sequencing-assign-index-task:visible').first
        task_id = await task_el.get_attribute("taskid") or "assign_index_task"
        if self._assign_index_task_id != task_id:
            self._assign_index_task_id = task_id
            self._assign_index_failed_positions.clear()

        # Inspect all items
        items = await target.evaluate('''() => {
            return Array.from(document.querySelectorAll('ef-sequencing-assign-index-item')).map((item, i) => {
                const btn = item.querySelector('.assessment-area');
                return {
                    i,
                    val: item.querySelector('.slot') ? item.querySelector('.slot').innerText.trim() : '',
                    isCorrect: btn ? (btn.classList.contains('is-correct') || btn.classList.contains('item-correct')) : false,
                    isIncorrect: btn ? (btn.classList.contains('is-incorrect') || btn.classList.contains('item-incorrect')) : false
                };
            });
        }''')

        if not items:
            return False

        # Record failed positions from current state
        for item in items:
            if item['isIncorrect'] and item['val'].isdigit():
                self._assign_index_failed_positions.add((item['i'], int(item['val'])))

        n_items = len(items)
        all_positions = set(range(1, n_items + 1))
        locked_positions = {int(item['val']) for item in items if item['isCorrect'] and item['val'].isdigit()}
        remaining_positions = sorted(list(all_positions - locked_positions))
        unlocked_items = [item['i'] for item in items if not item['isCorrect']]

        if not unlocked_items:
            check_btn = target.locator('button.check-task-button:not(.is-aria-disabled):not([disabled]):visible').first
            if await check_btn.count() > 0:
                await check_btn.click()
                await asyncio.sleep(1.5)
                return True
            return False

        # Find best permutation of remaining positions for unlocked items
        valid_perms = []
        for perm in itertools.permutations(remaining_positions):
            if all((unlocked_items[j], perm[j]) not in self._assign_index_failed_positions for j in range(len(unlocked_items))):
                valid_perms.append(perm)

        chosen_perm = valid_perms[0] if valid_perms else (list(itertools.permutations(remaining_positions))[0] if remaining_positions else [])

        # Assign positions via drawer
        for item_idx, target_pos in zip(unlocked_items, chosen_perm):
            curr_val = items[item_idx]['val']
            if curr_val != str(target_pos):
                print(f"  [Sequencing] Assigning Position {target_pos} to item {item_idx + 1}...")
                item_loc = target.locator('ef-sequencing-assign-index-item').nth(item_idx)
                btn = item_loc.locator('button.assessment-area')
                await btn.click()
                await asyncio.sleep(0.4)
                opt = target.locator(f'div.drawer-option[aria-label="Position {target_pos}"]').first
                if await opt.count() > 0:
                    await opt.click()
                    await asyncio.sleep(0.4)

        # Check if check button is enabled
        check_btn = target.locator('button.check-task-button:not(.is-aria-disabled):not([disabled]):visible').first
        if await check_btn.count() > 0:
            print("  [Sequencing] Submitting assign-index sequence...")
            await check_btn.click()
            await asyncio.sleep(1.5)

            # Re-read assessment to record feedback immediately
            res = await target.evaluate('''() => {
                return Array.from(document.querySelectorAll('ef-sequencing-assign-index-item')).map((item, i) => {
                    const btn = item.querySelector('.assessment-area');
                    return {
                        i,
                        val: item.querySelector('.slot') ? item.querySelector('.slot').innerText.trim() : '',
                        isCorrect: btn ? (btn.classList.contains('is-correct') || btn.classList.contains('item-correct')) : false,
                        isIncorrect: btn ? (btn.classList.contains('is-incorrect') || btn.classList.contains('item-incorrect')) : false
                    };
                });
            }''')
            for r in res:
                if r['isIncorrect'] and r['val'].isdigit():
                    self._assign_index_failed_positions.add((r['i'], int(r['val'])))
            return True

        return True

    async def _submit_and_record(self, target: Page | Frame, check_btn, full_display: list[str]) -> bool:
        """Clicks Check, reads per-token assessment, records invalid token positions, and resets unconfirmed tokens."""
        print(f"  [Sequencing] Submitting sequence: {' '.join(full_display)}...")
        await self.sleep_delay(0.4, 0.7)
        await check_btn.click()

        # Wait 0.7s for Angular assessment classes to render before Efekta's 1500ms reset timer
        await asyncio.sleep(0.7)

        # Check if Next button got enabled
        next_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next")'
        ).first
        if await next_btn.count() > 0:
            print("  [Sequencing] Sequence accepted! Next is enabled.")
            self._failed_permutations.clear()
            self._invalid_token_positions.clear()
            return True

        # Read assessment from DOM elements
        assessment = await target.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.textContent.trim();
                return (b.textContent || '').split('\n')[0].trim();
            };
            const isItemCorrect = (el) => {
                if (!el) return false;
                if (el.classList.contains('is-correct') || el.classList.contains('item-correct')) return true;
                if (el.querySelector('.is-correct, .item-correct, .correct-circle, ef-svg-thumbs-up, [id="thumbs-up"]')) return true;
                return false;
            };
            const isItemIncorrect = (el) => {
                if (!el) return false;
                if (el.classList.contains('is-incorrect') || el.classList.contains('item-incorrect')) return true;
                if (el.querySelector('.is-incorrect, .item-incorrect, .incorrect-circle, ef-svg-thumbs-down, [id="thumbs-down"]')) return true;
                return false;
            };
            const items = Array.from(document.querySelectorAll('.ordered-item-container > li'));
            const orderedEls = items.length > 0 ? items : Array.from(document.querySelectorAll('.ordered-item-container ef-sequencing-tap-option-item'));
            return orderedEls.map((el, i) => ({
                index: i,
                word: extractWord(el),
                isCorrect: isItemCorrect(el),
                isIncorrect: isItemIncorrect(el)
            }));
        }''')

        self._failed_permutations.add(tuple(full_display))

        # Identify the first incorrect position
        first_failed_idx = None
        for item in assessment:
            idx = item['index']
            if item['isIncorrect'] or not item['isCorrect']:
                first_failed_idx = idx
                break

        if first_failed_idx is not None and first_failed_idx < len(full_display):
            failed_word = full_display[first_failed_idx]
            self._invalid_token_positions.add((failed_word, first_failed_idx))
            print(f"  [Sequencing] Word '{failed_word}' incorrect at position {first_failed_idx}. Excluded from slot {first_failed_idx}.")
        elif len(full_display) > 1:
            fallback_idx = 0
            self._invalid_token_positions.add((full_display[fallback_idx], fallback_idx))

        # Wait for Efekta's reset animation to complete (incorrect items are returned to unordered pool)
        for _ in range(8):
            await asyncio.sleep(0.3)
            still_animating = await target.evaluate('''() => {
                const items = Array.from(document.querySelectorAll('.ordered-item-container > li, .ordered-item-container ef-sequencing-tap-option-item'))
                    .filter(el => el.tagName === 'LI' || !el.closest('li'));
                return items.some(el => el.classList.contains('is-incorrect') || el.classList.contains('item-incorrect'));
            }''')
            if not still_animating:
                break

        # Return any unconfirmed/incorrect items that still remain in the ordered container
        while True:
            ret = await target.evaluate('''() => {
                const items = Array.from(document.querySelectorAll('.ordered-item-container > li, .ordered-item-container ef-sequencing-tap-option-item'))
                    .filter(el => el.tagName === 'LI' || !el.closest('li'));
                for (const item of items) {
                    const isCorrect = item.classList.contains('is-correct') || item.classList.contains('item-correct') || item.querySelector('.is-correct, .item-correct, .correct-circle, ef-svg-thumbs-up, [id="thumbs-up"]');
                    if (!isCorrect) {
                        const b = item.querySelector('button') || (item.tagName === 'BUTTON' ? item : null);
                        if (b) {
                            b.click();
                            return true;
                        }
                    }
                }
                return false;
            }''')
            if not ret:
                break
            await asyncio.sleep(0.3)

        return True

    async def handle(self, target: Page | Frame) -> bool:
        # Check if assign index task is active (ef-sequencing-assign-index-task)
        assign_index = target.locator('ef-sequencing-assign-index-task:visible')
        if await assign_index.count() > 0:
            return await self._handle_assign_index(target)

        # Check if CDK Drag and Drop column sorting is active (ef-sequencing-sort-column-task)
        sort_column = target.locator('ef-sequencing-sort-column-task:visible')
        tap_task = target.locator('ef-sequencing-tap-option-task:visible, .unordered-item-container:visible')
        if await sort_column.count() > 0 and await tap_task.count() == 0:
            return await self._handle_cdk_drag(target)

        check_btn = target.locator('button.check-task-button:visible').first

        # Collect all words in the exercise to detect task changes (MUST inspect both ordered and unordered)
        all_words = await target.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.textContent.trim();
                return (b.textContent || '').split('\n')[0].trim();
            };
            const items = Array.from(document.querySelectorAll('.ordered-item-container > li'));
            const orderedEls = items.length > 0 ? items : Array.from(document.querySelectorAll('.ordered-item-container ef-sequencing-tap-option-item'));
            const ordered = orderedEls.map(extractWord).filter(Boolean);
            const unordered = Array.from(document.querySelectorAll('.unordered-item-container button')).map(extractWord).filter(Boolean);
            return [...ordered, ...unordered];
        }''')
        self._check_task_reset(all_words)

        # 1. Inspect active state of ordered and unordered containers
        state = await target.evaluate(r'''() => {
            const extractWord = (b) => {
                if (!b) return '';
                const el = b.querySelector('[data-qa="markdown-element-container"]');
                if (el) return el.textContent.trim();
                return (b.textContent || '').split('\n')[0].trim();
            };
            const isItemCorrect = (el) => {
                if (!el) return false;
                if (el.classList.contains('is-correct') || el.classList.contains('item-correct')) return true;
                if (el.querySelector('.is-correct, .item-correct, .correct-circle, ef-svg-thumbs-up, [id="thumbs-up"]')) return true;
                return false;
            };

            const items = Array.from(document.querySelectorAll('.ordered-item-container > li'));
            const orderedEls = items.length > 0 ? items : Array.from(document.querySelectorAll('.ordered-item-container ef-sequencing-tap-option-item'));

            // STRICT CONTINUOUS PREFIX from index 0:
            // Stop immediately at the first non-correct element so that any words after a gap are NOT locked.
            const lockedPrefix = [];
            for (let i = 0; i < orderedEls.length; i++) {
                const item = orderedEls[i];
                if (isItemCorrect(item)) {
                    lockedPrefix.push(extractWord(item));
                } else {
                    break;
                }
            }

            const unassessedOrdered = orderedEls.slice(lockedPrefix.length).map(extractWord).filter(Boolean);
            const unorderedWords = Array.from(document.querySelectorAll(
                '.unordered-item-container button:not(.is-hidden):not([hidden])'
            ))
                .filter(b => b.offsetParent !== null && !b.classList.contains('is-hidden') && !b.hasAttribute('hidden'))
                .map(extractWord).filter(Boolean);
            const checkBtn = document.querySelector('button.check-task-button');
            const checkEnabled = checkBtn && !checkBtn.disabled && !checkBtn.classList.contains('mat-mdc-button-disabled') && !checkBtn.classList.contains('is-aria-disabled');
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

        # 2. If all items are already ordered and Check button is enabled, submit
        if not unordered_words and check_enabled:
            current_full = locked_prefix + unassessed_ordered
            return await self._submit_and_record(target, check_btn, current_full)

        # 3. If there are unassessed buttons in ordered container while unordered pool is not empty, reset them
        if unassessed_ordered and unordered_words:
            print("  [Sequencing] Resetting unassessed ordered tokens to pool...")
            while True:
                ret = await target.evaluate('''() => {
                    const items = Array.from(document.querySelectorAll('.ordered-item-container > li, .ordered-item-container ef-sequencing-tap-option-item'))
                        .filter(el => el.tagName === 'LI' || !el.closest('li'));
                    for (const item of items) {
                        const isCorrect = item.classList.contains('is-correct') || item.classList.contains('item-correct') || item.querySelector('.is-correct, .item-correct, .correct-circle, ef-svg-thumbs-up, [id="thumbs-up"]');
                        if (!isCorrect) {
                            const b = item.querySelector('button') || (item.tagName === 'BUTTON' ? item : null);
                            if (b) {
                                b.click();
                                return true;
                            }
                        }
                    }
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
                if (el) return el.textContent.trim();
                return (b.textContent || '').split('\n')[0].trim();
            };
            return Array.from(document.querySelectorAll('.unordered-item-container button:not(.is-hidden):not([hidden])'))
                .filter(b => b.offsetParent !== null && !b.classList.contains('is-hidden') && !b.hasAttribute('hidden'))
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
                    if (el) return el.textContent.trim();
                    return (b.textContent || '').split('\n')[0].trim();
                };
                const btns = Array.from(document.querySelectorAll(
                    '.unordered-item-container button:not(.is-hidden):not([hidden])'
                )).filter(b => b.offsetParent !== null && !b.classList.contains('is-hidden') && !b.hasAttribute('hidden'));
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
            return await self._submit_and_record(target, check_btn, full_display)

        return True
