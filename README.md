# Efekta Self-Study Automation Bot

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Patchright](https://img.shields.io/badge/Engine-Patchright%20%2F%20CDP-2b5c8f?style=flat)](https://github.com/Kaliiiiiiiiii-Jy/patchright)
[![Architecture](https://img.shields.io/badge/Architecture-CDP%20%2B%20Modular%20Handlers-success?style=flat)](docs/ARCHITECTURE.md)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An autonomous, enterprise-grade Python bot designed to automatically navigate, solve, and complete curriculum units on the [Efekta Self-Study Portal](https://learn.better.efekta.com/gap/ui/self-study).

Built to seamlessly handle complex modern single-page applications (Angular, React, nested iframes) without getting blocked by bot-detection barriers or failing interactive audio/visual tasks.

---

## Key Highlights

- **100% Cloudflare Turnstile Immunity**: Connects over the **Chrome DevTools Protocol (`CDP`)** directly to a native Google Chrome instance (`port 9222`). Zero synthetic clicks on Turnstile challenge checkboxes; validation passes organically with genuine device profiles.
- **Autonomous Multi-Unit Curriculum Solver**: Iterates across units and lessons (Units 1 through 6, 24 lessons total), automatically launching incomplete lessons and returning to the dashboard upon completion.
- **Microphone & Speech Evaluation Integration**: Bridges speaking tasks using macOS Text-To-Speech (`say`) synchronized with browser recording triggers, ensuring phonetic evaluation passes without manual voice interaction.
- **Combinatorial Grammar Sequencing**: Employs an English grammar transition matrix (pronoun $\to$ verb $\to$ infinitive $\to$ prepositional phrase) to solve scrambled word sentences in 1–2 attempts instead of $O(N!)$ brute force.
- **Video & Media Accelerator**: Natively speeds up media playback (`playbackRate = 4.0`), automatically advancing once interactive prompts or completion markers unlock.
- **Anti-Loop Circuit Breakers**: Guards against UI stalls with heuristic rotation, attempt-capping on speaking retries, and prioritized navigation forward over redundant reviews.

---

## Supported Task Types

| Module | Task Type | Implementation Details |
|---|---|---|
| **Media Playback** | Video / Audio Introductions | Sets media elements to `playbackRate = 4.0`; automatically detects unlocked `Next` buttons. |
| **Speaking** | Repeat-after-me & MC Speech | Extracts target phrase; plays synthesized audio into mic; caps retries at 1–2 attempts before advancing. |
| **Sequencing** | Tap-to-Order & Drag Columns | Bigram grammar scoring sorts candidate permutations; keyboard controls reorder Angular CDK drag columns. |
| **Gap Fill** | Fill-in-the-Blanks | Scans unfilled `.selection-gap-button` elements and rotates bottom drawer selections. |
| **Matching** | Card & Concept Associations | Pairs associated definitions and terms across two-column layouts. |
| **Categorisation** | Column Card Sorting | Classifies draggable or selectable concepts into their respective category bins. |
| **Multiple Choice** | Radio Buttons & Choice Cards | Identifies question cards; tracks unselected options; iterates untried choices until submitted. |
| **Writing** | Essays & Freeform Responses | Generates topic-compliant responses meeting minimum word count thresholds; self-scores 5-star rubric. |
| **Navigation** | Transitions & Dialogs | Automatically dismisses dialogs (`Okay, got it`), launches steps, and returns to the unit overview. |

---

## Repository Structure

```text
efekta/
├── bot.py                  # Main autonomous state machine and multi-unit loop
├── config.py               # Environment configuration and parameter parser
├── handlers/               # Modular interaction handlers
│   ├── base.py             # Abstract BaseHandler interface
│   ├── cloudflare.py       # Passive Turnstile observer
│   ├── media.py            # Audio/video acceleration handler
│   ├── speaking.py         # TTS audio capture and speech evaluation handler
│   ├── multiple_choice.py  # Choice cards and radio selector handler
│   ├── gap_fill.py         # Fill-in-the-blank drawer handler
│   ├── sequencing.py       # Grammar-scored word token sequencing handler
│   ├── categorisation.py   # Multi-column classification handler
│   ├── matching.py         # Associative pair matching handler
│   ├── writing.py          # Writing challenge composer and rubric rater
│   └── navigation.py       # Steppers, dialogs, check/submit, and next handler
├── tests/                  # Test suite
│   ├── mock_server.py      # Local aiohttp server simulating Efekta UI & API
│   ├── test_solver.py      # End-to-end integration test with mock web server
│   ├── test_sequencing.py  # Grammar scoring unit tests
│   └── test_categorisation_and_matching.py
├── docs/                   # Documentation and ADRs
│   ├── ARCHITECTURE.md     # In-depth architectural design
│   └── decisions/          # Architecture Decision Records (ADR-001, ADR-002, ADR-003)
├── start_chrome.sh         # Helper script to launch native Chrome with CDP
├── requirements.txt        # Python dependency manifest
└── pytest.ini              # Pytest configuration
```

---

## Getting Started

### 1. Prerequisites
- **macOS** (for native `say` speech synthesis; Linux/Windows can run with virtual audio or mock devices)
- **Google Chrome** installed
- **Python 3.14+**

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/abbakkio/efekta-bot.git
cd efekta-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy the environment template and provide your Efekta credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
EFEKTA_EMAIL=your_email@example.com
EFEKTA_PASSWORD=your_password_here
HEADLESS=false
MIN_DELAY_SEC=1.0
MAX_DELAY_SEC=2.5
```

---

## Running the Bot

### Option A: Fully Automated Launch
The bot will automatically check if Google Chrome is listening on port `9222`. If not, it will launch native Chrome with your persistent profile and connect over CDP:

```bash
python bot.py
```

### Option B: Manual Chrome Startup
You can launch Chrome explicitly with remote debugging enabled using the provided helper script:

```bash
./start_chrome.sh
python bot.py
```

---

## Verification & Testing

The repository includes a comprehensive test suite with a local `aiohttp` mock server simulating the complete Efekta UI/API workflow:

```bash
# Run all unit and integration tests
pytest tests/ -v
```

All 6 test suites verify:
- End-to-end solver execution across media, speaking, and multiple choice steps.
- Grammar scoring accuracy on sentence permutations.
- Column distribution for categorisation and pair association.

---

## Architecture & Decisions

Detailed design documents and Architectural Decision Records are located in `docs/`:
- [Architecture Overview](docs/ARCHITECTURE.md)
- [ADR-001: Native Google Chrome over CDP with Patchright](docs/decisions/0001-cdp-and-patchright-architecture.md)
- [ADR-002: macOS Speech Synthesis & Navigation Priority](docs/decisions/0002-tts-audio-injection-and-navigation-priority.md)
- [ADR-003: Permutation Heuristics for Word Sequencing](docs/decisions/0003-permutation-heuristics-for-sequencing.md)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
