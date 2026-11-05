# Task Checklist: Efekta Bot

## Task 1: Project Setup & Dependencies
**Description:** Configure repository metadata, dependencies, and environment files.
- [x] Requirements file (`requirements.txt`)
- [x] Environment example (`.env.example`)
- [x] Git ignore (`.gitignore`)
- [x] Config module (`config.py`)
- Acceptance: Environment loads variables cleanly without errors.
- Verify: Verified virtual environment and config loading.

## Task 2: Base Handler & Specialized Exercise Handlers
**Description:** Implement modular handlers for Media, Speaking, Multiple Choice, and Navigation.
- [x] `handlers/base.py` (BaseHandler class)
- [x] `handlers/media.py` (detects audio/video, plays to completion)
- [x] `handlers/speaking.py` (handles mic recording with fake stream)
- [x] `handlers/multiple_choice.py` (selects radio/choice cards)
- [x] `handlers/navigation.py` (clicks Check, Submit, Next, Continue)
- Acceptance: Each handler has `can_handle()` and `handle()` methods.
- Verify: Verified imports and methods.

## Task 3: Bot Runner & Browser Context Setup
**Description:** Implement `bot.py` with Chromium WebRTC flag initialization, login flow, and state-machine loop.
- [x] `init_browser_context()` with `--use-fake-ui-for-media-stream` and `--use-fake-device-for-media-stream`
- [x] `login_if_needed()` with session caching in `session_state.json`
- [x] `solve_step()` evaluating handlers in priority order
- [x] Screenshot on error handling
- Acceptance: The bot starts, attaches handlers, and handles navigation.
- Verify: Verified with test run and system Google Chrome.

## Task 4: Local Test Server & Integration Tests (TDD)
**Description:** Implement mock Efekta server and end-to-end integration test verifying full unit progression.
- [x] `tests/mock_server.py` serving a simulated self-study unit (listening slide, speaking slide with MediaRecorder, multiple choice, completion)
- [x] `tests/test_solver.py` running the bot through the mock server
- Acceptance: Playwright traverses all slides and reaches the finish screen.
- Verify: `pytest -v tests/test_solver.py` passed with 100% success in 20.20s.
