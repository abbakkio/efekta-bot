import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from handlers.speaking import SpeakingHandler

@pytest.mark.asyncio
async def test_speaking_can_handle_when_advance_btn_present():
    handler = SpeakingHandler()
    mock_target = MagicMock()
    advance_loc = MagicMock()
    advance_loc.count = AsyncMock(return_value=1)
    
    mock_target.locator.return_value.first = advance_loc
    assert await handler.can_handle(mock_target) is False

@pytest.mark.asyncio
async def test_speaking_can_handle_when_recorder_present():
    handler = SpeakingHandler()
    mock_target = MagicMock()
    
    # 1. advance_btn count = 0
    # 2. clickable_options count = 0
    # 3. recorder_button count = 1
    def locator_side_effect(selector):
        loc = MagicMock()
        if "next-task-button" in selector or "main-next" in selector:
            loc.first.count = AsyncMock(return_value=0)
        elif "option-button" in selector or "radio" in selector:
            loc.count = AsyncMock(return_value=0)
        elif "audio-record-or-play" in selector or "audio-recorder-btn" in selector:
            loc.first.count = AsyncMock(return_value=1)
        else:
            loc.count = AsyncMock(return_value=0)
            loc.first.count = AsyncMock(return_value=0)
        return loc

    mock_target.locator.side_effect = locator_side_effect
    assert await handler.can_handle(mock_target) is True

@pytest.mark.asyncio
async def test_speaking_skips_immediately_when_evaluated_incorrect():
    handler = SpeakingHandler()
    mock_target = MagicMock()
    
    # Evaluate returns empty dom_incorrect and empty task_sig
    mock_target.evaluate = AsyncMock(return_value="")
    mock_target.page = MagicMock()
    mock_target.page.context = None

    rec_btn = MagicMock()
    rec_btn.count = AsyncMock(return_value=1)
    rec_btn.get_attribute = AsyncMock(side_effect=lambda attr: "Not quite right, please try again!" if attr == "aria-label" else "audio-recorder-btn no-pointer")

    skip_btn = MagicMock()
    skip_btn.count = AsyncMock(return_value=1)
    skip_btn.click = AsyncMock()

    def locator_side_effect(selector):
        loc = MagicMock()
        if "audio-record-or-play" in selector or "audio-recorder-btn" in selector:
            return MagicMock(first=rec_btn)
        elif "skip" in selector or "SKIP" in selector:
            return MagicMock(first=skip_btn)
        elif "ef-multiple-choice-speech-task:visible" in selector:
            loc.count = AsyncMock(return_value=0)
            return loc
        elif "ef-svg-replay" in selector:
            loc.count = AsyncMock(return_value=1)
            return loc
        else:
            loc.count = AsyncMock(return_value=0)
            loc.first = MagicMock(count=AsyncMock(return_value=0))
            return loc

    mock_target.locator.side_effect = locator_side_effect

    with patch.object(handler, "sleep_delay", new=AsyncMock()):
        result = await handler.handle(mock_target)
        assert result is True
        skip_btn.click.assert_awaited_once()

@pytest.mark.asyncio
async def test_speaking_records_and_stops_on_ready_state():
    handler = SpeakingHandler()
    mock_target = MagicMock()
    mock_target.evaluate = AsyncMock(return_value="")
    mock_target.page = MagicMock()
    mock_target.page.context = None

    rec_btn = MagicMock()
    rec_btn.count = AsyncMock(return_value=1)
    rec_btn.get_attribute = AsyncMock(side_effect=lambda attr: "Click to record your answer" if attr == "aria-label" else "audio-recorder-btn")
    rec_btn.click = AsyncMock()
    rec_btn.locator.return_value.count = AsyncMock(return_value=0)

    skip_btn = MagicMock()
    skip_btn.count = AsyncMock(return_value=1)

    def locator_side_effect(selector):
        loc = MagicMock()
        if "audio-record-or-play" in selector or "audio-recorder-btn" in selector:
            return MagicMock(first=rec_btn)
        elif "skip" in selector or "SKIP" in selector:
            return MagicMock(first=skip_btn)
        elif "ef-multiple-choice-speech-task:visible" in selector:
            loc.count = AsyncMock(return_value=0)
            return loc
        elif "ef-svg-replay" in selector:
            loc.count = AsyncMock(return_value=0)
            return loc
        else:
            loc.count = AsyncMock(return_value=0)
            loc.first = MagicMock(count=AsyncMock(return_value=0))
            return loc

    mock_target.locator.side_effect = locator_side_effect

    with patch.object(handler, "_speak_phrase_aloud") as mock_speak, \
         patch.object(handler, "_wait_for_evaluation", new=AsyncMock()) as mock_wait:
        result = await handler.handle(mock_target)
        assert result is True
        rec_btn.click.assert_awaited()
        mock_speak.assert_called_once()
        mock_wait.assert_awaited_once()
