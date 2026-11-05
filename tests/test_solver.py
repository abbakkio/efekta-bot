import pytest
from aiohttp import web
from patchright.async_api import async_playwright
import bot
from tests.mock_server import create_mock_app

@pytest.mark.asyncio
async def test_full_unit_automation_end_to_end(tmp_path):
    """Verifies that the bot autonomously completes login, media playback,

    speaking tasks with fake audio, multiple choice, and finishes the unit.
    """
    app = create_mock_app()
    runner = web.AppRunner(app)
    await runner.setup()
    port = 8899
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    target_url = f"http://127.0.0.1:{port}/gap/ui/self-study"

    try:
        async with async_playwright() as playwright:
            # For headless unit testing, launch isolated test context directly
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(tmp_path / "test_profile"),
                channel="chrome",
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--autoplay-policy=no-user-gesture-required",
                ],
                ignore_default_args=["--enable-automation"],
                permissions=["microphone"],
            )
            page = context.pages[0] if context.pages else await context.new_page()

            await bot.login_if_needed(page, context, target_url=target_url)

            success = await bot.solve_unit(page, context, max_steps=25)

            assert success is True, "Bot failed to finish unit"

            completed_text = await page.locator(".unit-completed").text_content()
            assert "Unit Complete" in completed_text
            print(f"[TEST PASS] Completed unit with content: {completed_text.strip()}")

            await context.close()
    finally:
        await runner.cleanup()
