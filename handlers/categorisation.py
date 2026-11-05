import asyncio
import re
from patchright.async_api import Page, Frame
from .base import BaseHandler

SEMANTIC_CLUSTERS = {
    "positive": [
        "amazing", "great", "good", "catchy", "addictive", "love", "like",
        "fantastic", "wonderful", "excellent", "cool", "enjoy", "best",
        "favorite", "favourite", "beautiful", "perfect", "positive", "high notes",
        "impressive", "brilliant", "superb", "terrific", "range"
    ],
    "negative": [
        "annoying", "bad", "terrible", "awful", "hate", "dislike", "isn't",
        "aren't", "don't", "not", "poor", "boring", "negative", "con",
        "horrible", "rubbish", "much", "weak", "loud", "flat", "dull", "offensive"
    ],
    "pros": [
        "advantage", "benefit", "good", "positive", "pro", "gain", "strength"
    ],
    "cons": [
        "disadvantage", "drawback", "bad", "negative", "con", "loss", "weakness"
    ],
    "formal": [
        "sincerely", "regards", "dear", "furthermore", "however", "therefore", "inquire", "apologize"
    ],
    "informal": [
        "hey", "hi", "cheers", "bye", "cool", "stuff", "thanks", "gonna", "wanna"
    ],
    "places": [
        "club", "hall", "venue", "stadium", "arena", "theater", "theatre", "park",
        "city", "street", "house", "home", "room", "school", "office", "station",
        "airport", "building", "center", "centre", "hotel", "restaurant", "bar",
        "cafe", "museum", "gallery", "store", "shop", "market", "cinema"
    ],
    "people": [
        "artist", "fan", "dj", "disc jockey", "singer", "musician", "performer",
        "dancer", "actor", "actress", "crowd", "audience", "member", "band",
        "teacher", "student", "friend", "family", "doctor", "worker", "colleague",
        "director", "producer", "guest", "visitor", "speaker", "listener"
    ],
    "music": [
        "instrumental", "electric", "acoustic", "rock", "pop", "jazz", "classical",
        "blues", "hip hop", "rap", "guitar", "drum", "drums", "piano", "violin",
        "song", "track", "album", "tune", "melody", "sound", "volume", "genre",
        "concert", "performance", "beat", "rhythm", "lyrics", "audio"
    ],
    "food": [
        "pizza", "burger", "salad", "bread", "cheese", "meat", "fish", "chicken",
        "fruit", "apple", "banana", "vegetable", "soup", "dessert", "cake"
    ],
    "drinks": [
        "water", "coffee", "tea", "juice", "soda", "wine", "beer", "milk"
    ],
}

class CategorisationHandler(BaseHandler):
    """Handles Efekta categorisation tasks (ef-categorisation-task)

    by grouping option items into their target categories with failure memory and polarity rules.
    """

    def __init__(self):
        super().__init__()
        self._failed_pairs = set()

    async def can_handle(self, target: Page | Frame) -> bool:
        task = target.locator("ef-categorisation-task:visible")
        if await task.count() > 0:
            options = target.locator("button.item.option:visible")
            targets = target.locator("button.item.target:visible")
            if await options.count() > 0 and await targets.count() > 0:
                return True
        return False

    def _clean_text(self, text: str) -> str:
        """Removes duplicate lines from innerText (e.g. 'club\\nclub' -> 'club')."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return lines[0] if lines else text.strip()

    def _match_category(self, option_text: str, category_names: list[str]) -> str:
        """Determines best category for an option using keyword matching and failure memory."""
        # Filter out categories that already failed for this option
        available = [c for c in category_names if (option_text, c) not in self._failed_pairs]
        if not available:
            # If all failed, clear memory for this option to prevent deadlocks
            self._failed_pairs = {p for p in self._failed_pairs if p[0] != option_text}
            available = category_names

        clean_opt = option_text.lower().strip()
        opt_words = set(re.findall(r"\b\w+\b", clean_opt))

        # Check positive/negative polarity specifically
        pos_score = len(opt_words.intersection(set(SEMANTIC_CLUSTERS["positive"])))
        neg_score = len(opt_words.intersection(set(SEMANTIC_CLUSTERS["negative"])))
        if "high notes" in clean_opt:
            pos_score += 2
        if any(neg_phrase in clean_opt for neg_phrase in ["isn't", "aren't", "don't", "not", "much of a"]):
            neg_score += 3

        for cat in available:
            cat_lower = cat.lower()
            if any(k in cat_lower for k in ["pos", "pro", "good", "like"]) and pos_score > neg_score:
                return cat
            if any(k in cat_lower for k in ["neg", "con", "bad", "dislike"]) and neg_score >= pos_score:
                return cat

        # Direct cluster matching
        best_cat = None
        max_overlap = -1

        for cat in available:
            cat_lower = cat.lower()
            cluster_keys = [k for k in SEMANTIC_CLUSTERS if k in cat_lower or cat_lower in k]
            for ck in cluster_keys:
                cluster_words = set(SEMANTIC_CLUSTERS[ck])
                overlap = len(opt_words.intersection(cluster_words))
                if overlap > max_overlap and overlap > 0:
                    max_overlap = overlap
                    best_cat = cat

            if any(w in cat_lower for w in opt_words) or any(w in clean_opt for w in cat_lower.split()):
                if max_overlap < 1:
                    max_overlap = 1
                    best_cat = cat

        if best_cat:
            return best_cat

        return available[0]

    async def handle(self, target: Page | Frame) -> bool:
        options_loc = target.locator("button.item.option:visible")
        targets_loc = target.locator("button.item.target:visible")

        opt_count = await options_loc.count()
        cat_count = await targets_loc.count()

        if opt_count == 0 or cat_count == 0:
            return False

        # Gather target category names
        categories = []
        for i in range(cat_count):
            cat_btn = targets_loc.nth(i)
            raw_text = await cat_btn.inner_text()
            aria_label = await cat_btn.get_attribute("aria-label") or ""
            clean_name = aria_label.replace("- category", "").strip() if "- category" in aria_label else self._clean_text(raw_text)
            categories.append(clean_name)

        # Process the first option item
        opt_btn = options_loc.first
        raw_opt_text = await opt_btn.inner_text()
        aria_label = await opt_btn.get_attribute("aria-label") or ""
        clean_opt = aria_label.replace("- option", "").strip() if "- option" in aria_label else self._clean_text(raw_opt_text)

        target_cat_name = self._match_category(clean_opt, categories)
        print(f"  [Categorisation] Assigning '{clean_opt}' -> category '{target_cat_name}'...")

        # Find the target button
        chosen_target_btn = None
        for i in range(cat_count):
            if categories[i] == target_cat_name:
                chosen_target_btn = targets_loc.nth(i)
                break
        if not chosen_target_btn:
            chosen_target_btn = targets_loc.first

        await self.sleep_delay(0.3, 0.5)

        # Select option if not already selected
        if await opt_btn.get_attribute("aria-pressed") != "true":
            await opt_btn.click()
            await asyncio.sleep(0.3)

        # Click target category
        await chosen_target_btn.click()
        # Efekta animation duration is 1250ms
        await asyncio.sleep(1.4)

        # Check if option was placed or rejected
        remaining_options = await target.evaluate("""() => {
            return Array.from(document.querySelectorAll("button.item.option")).map(b => b.innerText.split("\\n")[0].trim());
        }""")
        if clean_opt in remaining_options:
            print(f"  [Categorisation] Pair ('{clean_opt}', '{target_cat_name}') incorrect. Recording failure.")
            self._failed_pairs.add((clean_opt, target_cat_name))
        else:
            print(f"  [Categorisation] Successfully categorized '{clean_opt}' into '{target_cat_name}'!")

        return True
