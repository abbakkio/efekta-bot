import asyncio
import re
from patchright.async_api import Page, Frame
from .base import BaseHandler

class MatchingHandler(BaseHandler):
    """Handles Efekta matching exercises (ef-matching-task)

    by pairing matching options across columns (images-to-text, prompt-to-value, or split phrases).
    """

    def __init__(self):
        super().__init__()
        self._failed_pairs = set()

    async def can_handle(self, target: Page | Frame) -> bool:
        task = target.locator("ef-matching-task:visible")
        if await task.count() > 0:
            return True
        opts = target.locator("ef-matching-option:visible")
        return await opts.count() > 1

    def _extract_keywords(self, text: str) -> set[str]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        stop_words = {"the", "and", "with", "this", "that", "from", "for", "are", "was", "were", "image", "photo", "picture"}
        return {w for w in words if w not in stop_words}

    def _score_pair(self, left_text: str, right_text: str) -> int:
        """Scores semantic compatibility between a left prompt and a right value/phrase."""
        lt = left_text.lower().strip()
        rt = right_text.lower().strip()

        # Specific prompt-value patterns
        if "date" in lt or "day" in lt or "when" in lt:
            if re.search(r"\b\d{1,2}/\d{1,2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d+(?:st|nd|rd|th))\b", rt):
                return 100
        if "time" in lt or "clock" in lt:
            if re.search(r"\b\d{1,2}:\d{2}\b|\b(?:am|pm)\b", rt):
                return 100
        if "venue" in lt or "place" in lt or "where" in lt or "location" in lt:
            if any(w in rt for w in ["center", "hall", "club", "theatre", "theater", "stadium", "arena", "park", "street", "city"]):
                return 90
        if "disc jockey" in lt or "dj" in lt:
            if "dj" in rt or "turntable" in rt or "track" in rt:
                return 95
        if "artist" in lt or "group" in lt or "band" in lt or "singer" in lt:
            if any(w in rt for w in ["light", "and", "&", "band", "orchestra", "trio", "quartet"]) or (rt and rt[0].isupper()):
                return 80

        # Sentence completion rules
        # "Come" -> "on!"
        if "come" in lt and "on" in rt:
            return 95
        # "Don't" -> "be lazy"
        if "don't" in lt and ("be" in rt or "do" in rt or "forget" in rt or "worry" in rt):
            return 90
        # "You're such" -> "a couch potato" / "a ..."
        if "such" in lt and (rt.startswith("a ") or rt.startswith("an ")):
            return 90
        # "You'll have a" -> "great time"
        if lt.endswith(" a") and any(w in rt for w in ["great", "good", "fun", "blast", "wonderful"]):
            return 90
        # "I'll pay, and" -> "I'll drive"
        if lt.endswith("and") and (rt.startswith("i'll") or rt.startswith("i ")):
            return 90
        # "It'll be good for you" -> "to get out"
        if (lt.endswith("you") or "good for" in lt) and rt.startswith("to "):
            return 90

        # General keyword overlap
        l_words = self._extract_keywords(lt)
        r_words = self._extract_keywords(rt)
        overlap = len(l_words.intersection(r_words))

        # Stem / Substring match
        sub_score = 0
        for lw in l_words:
            if lw in rt:
                sub_score += 15
        for rw in r_words:
            if rw in lt:
                sub_score += 15

        return overlap * 20 + sub_score

    async def handle(self, target: Page | Frame) -> bool:
        advance_btn = target.locator('button:not([disabled]):visible:has-text("Next")').first
        if await advance_btn.count() > 0:
            return False

        options_loc = target.locator("ef-matching-option:visible")
        count = await options_loc.count()
        if count < 2:
            return False

        cards = []
        for i in range(count):
            opt = options_loc.nth(i)
            is_disabled = await opt.locator('.disabled, [aria-disabled="true"]').count() > 0
            if is_disabled:
                continue

            clickable = opt.locator('div[role="button"]').first
            if await clickable.count() == 0:
                clickable = opt

            img = opt.locator("img").first
            img_alt = (await img.get_attribute("alt") or "").strip() if await img.count() > 0 else ""

            raw_text = (await opt.inner_text()).strip()
            lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
            clean_text = lines[0] if lines else ""

            box = await opt.bounding_box()
            x = box["x"] if box else 0
            y = box["y"] if box else 0

            cards.append({
                "index": i,
                "clickable": clickable,
                "is_img": bool(img_alt),
                "alt": img_alt,
                "text": clean_text,
                "desc": img_alt if img_alt else clean_text,
                "x": x,
                "y": y
            })

        if len(cards) < 2:
            return False

        # Partition cards into Column A and Column B
        img_cards = [c for c in cards if c["is_img"]]
        txt_cards = [c for c in cards if not c["is_img"]]

        if img_cards and txt_cards:
            col_a = img_cards
            col_b = txt_cards
        else:
            x_values = sorted(list({round(c["x"]) for c in cards}))
            if len(x_values) >= 2:
                mid_x = (x_values[0] + x_values[-1]) / 2
                col_a = [c for c in cards if c["x"] <= mid_x]
                col_b = [c for c in cards if c["x"] > mid_x]
            else:
                half = len(cards) // 2
                col_a = cards[:half]
                col_b = cards[half:]

        if not col_a or not col_b:
            col_a = [cards[0]]
            col_b = [cards[1]]

        # Find best pair that hasn't previously failed
        candidates = []
        for a in col_a:
            for b in col_b:
                pair_key = f"{a['desc']}|||{b['desc']}"
                if pair_key in self._failed_pairs:
                    continue
                score = self._score_pair(a["desc"], b["desc"])
                candidates.append((score, a, b, pair_key))

        if not candidates:
            # If all tried combinations failed, reset failed cache
            self._failed_pairs.clear()
            candidates = [(self._score_pair(a["desc"], b["desc"]), a, b, f"{a['desc']}|||{b['desc']}") for a in col_a for b in col_b]

        candidates.sort(key=lambda item: item[0], reverse=True)
        best_score, first_card, second_card, pair_key = candidates[0]

        print(f"  [Matching] Pairing '{first_card['desc'][:20]}' <-> '{second_card['desc'][:20]}' (score={best_score})...")
        self._failed_pairs.add(pair_key)

        await self.sleep_delay(0.3, 0.6)
        await first_card["clickable"].click()
        await self.sleep_delay(0.3, 0.5)
        await second_card["clickable"].click()
        await self.sleep_delay(0.8, 1.2)

        return True
