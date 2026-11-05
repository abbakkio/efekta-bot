# ADR-002: macOS Speech Synthesis and Forward-Progress Navigation Priority

## Status
Accepted

## Date
2026-11-05

## Context
Efekta includes spoken response activities evaluated via microphone audio stream. If the environment runs headlessly or with silent microphone inputs, the speaking evaluator registers silence and rejects submissions with *"Not quite right, please try again!"*.

Additionally, when speaking items were skipped, the end-of-activity screen displayed two options:
- `Next`: Advance forward to the next step.
- `Finish skipped tasks`: Re-enter the skipped tasks to re-record them.

Previously, `NavigationHandler` checked `Finish skipped tasks` before checking `Next`. This led to an infinite loop where all tasks were skipped, the screen offered both buttons, the bot chose `Finish skipped tasks`, skipped all tasks again, and remained trapped indefinitely.

## Decision
1. **TTS Audio Playback**: During speaking recording, `SpeakingHandler` uses native macOS speech synthesis (`say -v Samantha "<target_phrase>"`) to play the target phrase aloud through the system speakers, which the microphone inputs.
2. **Strict Retry Capping**: Speaking items are limited to 1 attempt for repeat-after-me tasks and 2 attempts for multiple-choice speech, advancing via `SKIP` if evaluation fails.
3. **Forward-Progress Navigation Priority**: In `NavigationHandler`, enabled `Next`, `Start next step`, and `Continue` buttons are evaluated **before** `Finish skipped tasks` or `Finish skipped activities`.

## Consequences
- **Pros:**
  - Speech tasks receive genuine phonetic audio input and pass evaluation.
  - The solver is strictly prevented from entering infinite loops on optional skipped task reviews.
  - Lessons advance smoothly through completion thresholds (e.g. passing 3 of 4 required activities satisfies the step requirement).
- **Cons:**
  - Uses audio output on the host machine during speech exercises.
