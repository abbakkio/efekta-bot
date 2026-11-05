# Implementation Plan: Efekta Self-Study Bot

## Architecture Overview
The project is split into decoupled layers:
1. **Config Layer**: Manages credentials, timeouts, URLs, and delay profiles.
2. **Browser & Auth Layer**: Controls Chromium lifecycle with media stream flags and cookie session caching (`session_state.json`).
3. **Exercise Handlers**: Specialized modular classes (`MultipleChoiceHandler`, `SpeakingHandler`, `MediaPlaybackHandler`, `NavigationHandler`) implementing `can_handle()` and `handle()`.
4. **State Machine / Solver**: Iterative loop that scans the page DOM, evaluates handlers in priority order, takes the appropriate action, and verifies progress.
5. **Testing Harness**: Local simulated Efekta server providing realistic HTML/JS interactions (including MediaStream recording and audio playback) to verify that the bot autonomously navigates a complete unit.

## Implementation Steps
1. Foundations: Environment configuration, `.gitignore`, and `requirements.txt`.
2. Handlers:
   - `BaseHandler` contract
   - `MediaPlaybackHandler`
   - `SpeakingHandler`
   - `MultipleChoiceHandler`
   - `NavigationHandler`
3. Solver Loop & Auth in `bot.py`.
4. Mock Test Server in `tests/mock_server.py`.
5. Automated TDD Integration Test in `tests/test_solver.py`.
