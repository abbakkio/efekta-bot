import asyncio
import os
import subprocess
import time
import urllib.request
from patchright.async_api import async_playwright, Page, BrowserContext, TimeoutError
import config
from handlers import (
    MediaPlaybackHandler,
    SpeakingHandler,
    MultipleChoiceHandler,
    NavigationHandler,
    CloudflareHandler,
    GapFillHandler,
    CategorisationHandler,
    MatchingHandler,
    WritingHandler,
    SequencingHandler,
    FlashcardHandler,
)

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")
CDP_URL = "http://127.0.0.1:9222"

def is_cdp_ready() -> bool:
    """Checks if Chrome is active on port 9222."""
    try:
        urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=0.8)
        return True
    except Exception:
        return False

def launch_native_chrome():
    """Launches Google Chrome as a native macOS application process with remote debugging enabled."""
    print("[*] Launching native Google Chrome instance with your dedicated profile...")
    os.makedirs(PROFILE_DIR, exist_ok=True)
    subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--autoplay-policy=no-user-gesture-required",
        config.BASE_URL,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for the CDP endpoint to become responsive
    for _ in range(15):
        if is_cdp_ready():
            print("[+] Native Chrome is ready on port 9222.")
            return
        time.sleep(0.5)
    print("[!] Warning: Timed out waiting for Chrome debugging port.")

async def init_browser_context(playwright, headless: bool | None = None) -> BrowserContext:
    """Connects to native Google Chrome via CDP (100% Cloudflare Turnstile proof)."""
    # If not running on port 9222, launch native Chrome
    if not is_cdp_ready():
        launch_native_chrome()

    print("[*] Connecting to Chrome session over CDP...")
    browser = await playwright.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    print("[+] Successfully attached to Chrome!")
    return context

def is_auth_url(current_url: str) -> bool:
    """Checks if the URL is an Azure B2C, Okta, or Efekta login endpoint."""
    lower = current_url.lower()
    return "b2clogin.com" in lower or "login" in lower or "oauth" in lower or "authorize" in lower

def get_active_target_page(context: BrowserContext, fallback_page: Page) -> Page:
    """Returns the active lesson page if open (catalyst/study), or the most recently focused tab."""
    pages = context.pages
    if not pages:
        return fallback_page

    for p in reversed(pages):
        url = p.url.lower()
        if "catalyst" in url or "study" in url or "activity" in url or "lesson" in url:
            return p

    return pages[-1]

async def login_if_needed(page: Page, context: BrowserContext, target_url: str | None = None):
    """Handles both 1-step and 2-step (Azure B2C) authentication flows."""
    url = target_url or config.BASE_URL
    print(f"[*] Checking authentication status at {url}...")

    # If the page isn't already on efekta or auth, navigate
    if "efekta" not in page.url.lower() and not is_auth_url(page.url):
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(1.0)

    email_selector = '#email, input[type="email"], input[name="Email address"], input[name="email"], input[name="username"], input[placeholder*="email" i]'
    has_auth_inputs = await page.locator(email_selector).count() > 0 or await page.locator('input[type="password"]').count() > 0

    if is_auth_url(page.url) or has_auth_inputs:
        print("[*] Authentication required. Performing automated login...")

        if not config.EMAIL or not config.PASSWORD:
            print("[!] Note: EFEKTA_EMAIL or EFEKTA_PASSWORD not found in .env; please log in manually in Chrome.")

        # Step 1: Fill Email
        email_input = page.locator(email_selector).first
        if await email_input.count() > 0 and await email_input.is_visible():
            print(f"  [Auth] Entering email: {config.EMAIL}")
            await email_input.click()
            await email_input.fill(config.EMAIL)
            await email_input.dispatch_event("input")
            await email_input.dispatch_event("change")
            await asyncio.sleep(0.5)

            # Check if password field is already visible on the same page
            pw_step1 = page.locator('input[type="password"]:visible, #password:visible').first
            if await pw_step1.count() > 0:
                print("  [Auth] Entering password...")
                await pw_step1.click()
                await pw_step1.fill(config.PASSWORD)
                await pw_step1.dispatch_event("input")
                await pw_step1.dispatch_event("change")
                await asyncio.sleep(0.5)

            step1_btn = page.locator('#next:not([disabled]), button[type="submit"]:not([disabled]), button:not([disabled]):has-text("Continue"), button:not([disabled]):has-text("Log in"), button:not([disabled]):has-text("Sign in")').first
            if await step1_btn.count() > 0:
                print("  [Auth] Submitting step 1 (Continue)...")
                await step1_btn.click()
                await asyncio.sleep(2.0)

        # Step 2: Handle 2-Step Password input
        password_input = page.locator('input[type="password"]:visible, #password:visible').first
        if await password_input.count() == 0 and is_auth_url(page.url):
            try:
                print("  [Auth] Waiting for password input field...")
                await page.locator('input[type="password"]:visible, #password:visible').first.wait_for(state="visible", timeout=8000)
                password_input = page.locator('input[type="password"]:visible, #password:visible').first
            except TimeoutError:
                pass

        if await password_input.count() > 0 and await password_input.is_visible():
            print("  [Auth] Entering password...")
            await password_input.click()
            await password_input.fill(config.PASSWORD)
            await password_input.dispatch_event("input")
            await password_input.dispatch_event("change")
            await asyncio.sleep(0.5)

            login_btn = page.locator('button[type="submit"]:not([disabled]), button:not([disabled]):has-text("Log in"), button:not([disabled]):has-text("Sign in"), #next:not([disabled])').first
            if await login_btn.count() > 0:
                print("  [Auth] Submitting credentials...")
                await login_btn.click()

        print("[*] Awaiting redirect to Efekta portal...")
        try:
            await page.wait_for_url(lambda u: not is_auth_url(u), timeout=20000)
            print("[+] Successfully redirected to Efekta!")
        except Exception:
            if is_auth_url(page.url):
                print("[!] 2FA, OTP, or CAPTCHA may be active.")
                print("[*] Please complete any remaining step directly in the open Chrome window.")
                print("[*] Waiting up to 90 seconds for you...")
                try:
                    await page.wait_for_url(lambda u: not is_auth_url(u), timeout=90000)
                    print("[+] Detected successful authentication!")
                except Exception:
                    print("[!] Login wait timed out.")
    else:
        print("[+] Active session recognized.")

def get_target_scope(page: Page):
    """Returns the embedded lesson-player frame if present, otherwise the page itself."""
    for frame in page.frames:
        if "lesson-player" in frame.url.lower():
            return frame
    return page

async def enter_lesson_if_on_dashboard(page: Page, context: BrowserContext) -> bool:
    """If currently on the course or self-study overview, clicks the next active lesson."""
    # 1. Check standard start/continue buttons
    start_lesson_btn = page.locator(
        'button:not([disabled]):visible:has-text("Continue lesson"), '
        'button:not([disabled]):visible:has-text("Start lesson"), '
        'button:not([disabled]):visible:has-text("Continue studying"), '
        'button:not([disabled]):visible:has-text("Start"), '
        'button:not([disabled]):visible:has-text("Get started"), '
        'a:visible:has-text("Continue lesson"), '
        'a:visible:has-text("Start lesson"), '
        'a:visible:has-text("Continue studying"), '
        '[data-testid*="start-lesson" i]:visible, '
        '[data-testid*="continue-lesson" i]:visible'
    ).first

    if await start_lesson_btn.count() > 0:
        btn_text = (await start_lesson_btn.text_content() or "Start Lesson").strip()
        print(f"[*] Dashboard detected. Clicking '{btn_text}' to launch active lesson...")
        await start_lesson_btn.click()
        await asyncio.sleep(3.0)

        active = get_active_target_page(context, page)
        if active and active != page:
            print(f"[*] Switched to newly opened lesson tab: {active.url}")
            await active.bring_to_front()
        return True

    # 2. Check lesson cards on the self-study overview (e.g. data-id="lesson-card-2")
    cards = page.locator(
        '[data-id^="lesson-card-"]:not([data-id*="image"]):not([data-id*="state"]):not([data-id*="title"]):not([data-id*="lesson-no"]):not([data-id*="lock"])'
    )
    count = await cards.count()
    if count > 0:
        for i in range(count):
            card = cards.nth(i)
            # Skip locked
            if await card.locator('[data-id*="lock-icon"]').count() > 0:
                continue
            # Skip completed
            if await card.locator('[data-id*="state-icon"], [aria-label*="complete" i]').count() > 0:
                continue

            link = card.locator('[role="link"], [tabindex="0"], a, button').first
            if await link.count() > 0:
                title_el = card.locator('[data-id*="title"]').first
                title = await title_el.inner_text() if await title_el.count() > 0 else f"Lesson {i+1}"
                print(f"[*] Dashboard detected. Launching next active lesson: {title}...")
                await link.click()
                await asyncio.sleep(3.0)
                return True

    return False

async def solve_step(scope, handlers: list) -> bool:
    """Evaluates all handlers against current page or frame scope. Returns True if an action was executed."""
    for handler in handlers:
        try:
            if await handler.can_handle(scope):
                handled = await handler.handle(scope)
                if handled:
                    if not isinstance(handler, NavigationHandler):
                        for h in handlers:
                            if isinstance(h, NavigationHandler):
                                h.reset_circuit_breakers()
                    return True
        except Exception as e:
            print(f"  [Handler Error] {handler.__class__.__name__}: {e}")
    return False

async def get_current_level(page: Page) -> str:
    """Detects current active level from the page header or content."""
    try:
        level_str = await page.evaluate(r'''() => {
            const btn = document.querySelector('[data-id="level-view-header-change-level-btn"]');
            if (btn && btn.innerText.trim()) return btn.innerText.trim();
            const h1 = document.querySelector('h1');
            if (h1 && /Level\s+\d+/i.test(h1.innerText)) {
                const m = h1.innerText.match(/Level\s+\d+/i);
                if (m) return m[0];
            }
            const el = Array.from(document.querySelectorAll('span, button, h2, h3, div')).find(
                e => e.children.length === 0 && /^Level\s+\d+$/i.test((e.innerText || '').trim())
            );
            if (el) return el.innerText.trim();
            return '';
        }''')
        if level_str:
            import re
            m = re.search(r'Level\s+(\d+)', level_str, re.IGNORECASE)
            if m:
                return f"Level {m.group(1)}"
            return level_str.strip().title()
        return "Active Level"
    except Exception:
        return "Active Level"

async def advance_to_next_level(page: Page) -> bool:
    """Navigates to change-level and advances to the next sequential level if available."""
    try:
        import re
        curr_level = await get_current_level(page)
        m = re.search(r'\d+', curr_level)
        if not m:
            return False
        curr_num = int(m.group(0))
        next_num = curr_num + 1

        print(f"[*] Attempting to advance from Level {curr_num} to Level {next_num}...")

        # Open change-level page via header button or direct URL
        change_btn = page.locator('[data-id="level-view-header-change-level-btn"]').first
        if await change_btn.count() > 0:
            await page.evaluate("() => document.querySelector('[data-id=\"level-view-header-change-level-btn\"]')?.click()")
            await asyncio.sleep(2.0)
        else:
            await page.goto("https://learn.better.efekta.com/gap/ui/self-study/change-level")
            await asyncio.sleep(2.0)

        # Look for Level {next_num} card and select it
        target_card_found = await page.evaluate(r'''(targetNum) => {
            const spans = Array.from(document.querySelectorAll('span, div')).filter(
                s => s.innerText.trim().toUpperCase() === `LEVEL ${targetNum}`
            );
            for (const s of spans) {
                const card = s.closest('[role="radio"], [role="button"], button, div[tabindex]');
                if (card) {
                    card.click();
                    return true;
                }
            }
            return false;
        }''', next_num)

        if not target_card_found:
            print(f"[!] Level {next_num} card not found or locked.")
            await page.goto("https://learn.better.efekta.com/gap/ui/self-study")
            await asyncio.sleep(2.0)
            return False

        await asyncio.sleep(1.0)
        confirm_btn = page.locator('[data-id="selfStudy-page-change-level-confirm-btn"]').first
        if await confirm_btn.count() > 0:
            await confirm_btn.click()
            await asyncio.sleep(3.0)
            new_level = await get_current_level(page)
            print(f"[+] Successfully transitioned to {new_level}!")
            return True

        await page.goto("https://learn.better.efekta.com/gap/ui/self-study")
        await asyncio.sleep(2.0)
        return False
    except Exception as e:
        print(f"[!] Error advancing to next level: {e}")
        try:
            await page.goto("https://learn.better.efekta.com/gap/ui/self-study")
        except Exception:
            pass
        return False

async def get_dashboard_progress(page: Page) -> tuple[int, int]:
    """Returns (completed_lessons, total_lessons) across all units on the dashboard."""
    try:
        cards = page.locator(
            '[data-id^="lesson-card-"]:not([data-id*="image"]):not([data-id*="state"]):not([data-id*="title"]):not([data-id*="lesson-no"]):not([data-id*="lock"])'
        )
        total = await cards.count()
        if total == 0:
            return 0, 0
        completed = 0
        for i in range(total):
            card = cards.nth(i)
            if await card.locator('[data-id*="state-icon"], [aria-label*="complete" i]').count() > 0:
                completed += 1
        return completed, total
    except Exception:
        return 0, 0

async def solve_unit(
    initial_page: Page,
    context: BrowserContext,
    target_completed_lessons: int | None = None,
    max_steps: int = 10000,
    continuous_levels: bool = True
) -> bool:
    """State machine loop that solves lessons sequentially for the active difficulty level (and subsequent levels if continuous)."""
    speaking_handler = SpeakingHandler()
    await speaking_handler.setup_context_routing(context)

    handlers = [
        CloudflareHandler(),
        speaking_handler,
        MatchingHandler(),
        CategorisationHandler(),
        SequencingHandler(),
        WritingHandler(),
        FlashcardHandler(),
        MultipleChoiceHandler(),
        GapFillHandler(),
        MediaPlaybackHandler(),
        NavigationHandler(),
    ]

    initial_level = await get_current_level(initial_page)
    goal_desc = f"target: {target_completed_lessons} lessons" if target_completed_lessons else "continuous active level mode"
    print(f"[*] Starting autonomous solver loop on {initial_level} ({goal_desc})...")
    idle_count = 0

    for step in range(1, max_steps + 1):
        target_page = get_active_target_page(context, initial_page)

        # 1. If on dashboard, check overall progress for the active level
        if "self-study" in target_page.url.lower() and "lesson-view" not in target_page.url.lower():
            completed, total = await get_dashboard_progress(target_page)
            curr_level = await get_current_level(target_page)

            if total > 0:
                print(f"[*] Dashboard Progress [{curr_level}]: {completed}/{total} lessons completed.")
                if target_completed_lessons and completed >= target_completed_lessons:
                    print(f"[🎉] Reached target progress: {completed}/{total} lessons completed!")
                    return True
                elif completed >= total:
                    print(f"[🎉] CONGRATULATIONS! All {completed}/{total} lessons completed for {curr_level}!")
                    if continuous_levels:
                        advanced = await advance_to_next_level(target_page)
                        if advanced:
                            idle_count = 0
                            await asyncio.sleep(2.0)
                            continue
                    return True

            if await enter_lesson_if_on_dashboard(target_page, context):
                idle_count = 0
                await asyncio.sleep(2.0)
                continue

        # 2. Check for completion indicator
        try:
            finish_indicator = target_page.locator(
                '[data-testid*="congratulations" i], .unit-completed, h1:has-text("Unit Complete"), h2:has-text("Congratulations")'
            ).first
            if await finish_indicator.count() > 0 and await finish_indicator.is_visible():
                completed, total = await get_dashboard_progress(target_page)
                curr_level = await get_current_level(target_page)
                if total > 0 and completed < total:
                    print(f"[*] Unit completion banner detected [{curr_level} ({completed}/{total})]. Advancing to next lesson...")
                    close_btn = target_page.locator('button:has-text("Back to"), button:has-text("Continue"), [aria-label*="close" i]').first
                    if await close_btn.count() > 0:
                        await close_btn.click()
                        await asyncio.sleep(2.0)
                        continue
                else:
                    print(f"[✓] Goal completed successfully in {step} steps!")
                    return True
        except Exception:
            pass

        # 3. Resolve active scope (iframe or root page) and solve active slide
        scope = get_target_scope(target_page)
        acted = await solve_step(scope, handlers)
        if acted:
            idle_count = 0
            await asyncio.sleep(0.8)
        else:
            idle_count += 1
            await asyncio.sleep(1.5)
            if idle_count >= 18:
                if "self-study" in target_page.url.lower() and "lesson-view" not in target_page.url.lower():
                    if await enter_lesson_if_on_dashboard(target_page, context):
                        idle_count = 0
                        continue
                if idle_count >= 20:
                    print("[?] No interactive element detected over 30s. Solver loop paused.")
                    break

    return False

async def run():
    async with async_playwright() as playwright:
        context = await init_browser_context(playwright)

        # Pick active tab
        page = None
        for p in context.pages:
            if "efekta" in p.url.lower() or "catalyst" in p.url.lower():
                page = p
                break
        if not page:
            page = context.pages[0] if context.pages else await context.new_page()

        try:
            await login_if_needed(page, context)
            await solve_unit(page, context)
        except KeyboardInterrupt:
            print("\n[*] Script interrupted by user.")
        except Exception as e:
            print(f"[!] Runtime error: {e}")
            active = get_active_target_page(context, page)
            if active:
                await active.screenshot(path="error_state.png")
                print(f"[*] Saved error screenshot to error_state.png")

if __name__ == "__main__":
    asyncio.run(run())
