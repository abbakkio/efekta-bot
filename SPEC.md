# Spec: Efekta Self-Study Automation Bot

## Objective
Build an autonomous, robust Python and Playwright bot that signs into `https://learn.better.efekta.com`, navigates to the self-study units, and completes the exercises without requiring user interaction. The bot must handle diverse exercise types, including multiple choice, listening/audio playback, and speaking (microphone) exercises.

## Tech Stack
- **Language**: Python 3.14+
- **Browser Automation**: Playwright (Chromium with WebRTC flags for fake audio device & media stream)
- **Configuration**: `python-dotenv` for credentials and environment settings
- **Testing**: `pytest`, `pytest-asyncio`, `aiohttp` for mock integration server

## Commands
```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Run Unit & Integration Tests (TDD)
pytest -v

# Run Bot in Headed Mode (for visual inspection)
python bot.py

# Run Bot in Headless Mode
HEADLESS=true python bot.py
```

## Project Structure
```text
efekta/
├── .env.example              # Template configuration
├── .gitignore                # Ignored items (session state, venv, screenshots)
├── requirements.txt          # Python dependencies
├── SPEC.md                   # Formal specification
├── tasks/
│   ├── plan.md               # Technical implementation plan
│   └── todo.md               # Gated task checklist
├── config.py                 # Settings & env loading
├── handlers/
│   ├── __init__.py
│   ├── base.py               # Abstract exercise handler interface
│   ├── multiple_choice.py    # Radio buttons, choice cards, option items
│   ├── speaking.py           # Microphone detection, fake audio streaming
│   ├── media.py              # Audio/video element playback accelerator
│   └── navigation.py         # Check, Submit, Next, and Continue buttons
├── bot.py                    # Main solver state machine & runner
└── tests/
    ├── __init__.py
    ├── mock_server.py        # Local aiohttp server simulating Efekta UI & API
    └── test_solver.py        # End-to-end integration test verifying full unit completion
```

## Code Style
- Clean, modular Python with type hints and async/await syntax.
- Small single-responsibility handlers implementing a shared `BaseHandler` interface.
- Randomized human-like jitter delays to prevent instant-completion rate-limiting.

## Testing Strategy
- **Unit / Handler Tests**: Test individual handlers against DOM fixtures.
- **End-to-End Integration Tests**: Run a mock web server serving a full simulated Efekta self-study unit (Login -> Listening Slide -> Speaking Slide with MediaRecorder -> Multiple Choice Slide -> Finish Screen).
- Automated tests run Playwright in headless mode to verify that the solver traverses from start to finish without stalling.

## Boundaries
- **Always do**: Grant fake microphone permissions via browser flags; persist session cookies to avoid re-login prompts; save screenshot on unhandled error.
- **Ask first**: Making unprompted network calls to third-party endpoints or storing plaintext credentials in Git.
- **Never do**: Commit passwords or actual session tokens to version control; run with 0ms delays in production mode.

## Success Criteria
1. Bot automatically initializes Chromium with `--use-fake-ui-for-media-stream` and `--use-fake-device-for-media-stream`.
2. Bot can authenticate using email/password and persist/reuse `session_state.json`.
3. Bot detects and handles multiple-choice choices, clicking options and checking answers.
4. Bot detects speaking tasks, triggers recording, sustains audio capture, and finalizes the recording.
5. Bot detects audio elements, triggers playback, and waits for audio to finish before advancing.
6. The end-to-end test suite passes completely against the local simulated Efekta server.
