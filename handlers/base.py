from abc import ABC, abstractmethod
import asyncio
import random
from patchright.async_api import Page, Frame
import config

class BaseHandler(ABC):
    """Abstract base handler for an exercise type or UI interaction."""

    async def sleep_delay(self, min_sec: float | None = None, max_sec: float | None = None):
        """Asynchronously pause for a human-like duration."""
        min_s = config.MIN_DELAY_SEC if min_sec is None else min_sec
        max_s = config.MAX_DELAY_SEC if max_sec is None else max_sec
        if max_s > min_s and max_s > 0:
            await asyncio.sleep(random.uniform(min_s, max_s))
        elif min_s > 0:
            await asyncio.sleep(min_s)

    @abstractmethod
    async def can_handle(self, target: Page | Frame) -> bool:
        """Return True if this handler recognizes the active UI element or task."""
        pass

    @abstractmethod
    async def handle(self, target: Page | Frame) -> bool:
        """Perform the appropriate interaction and return True if action succeeded."""
        pass

