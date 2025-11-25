# Learning Tool

A small CLI learning companion written in Python 3.11+.

It is designed with explicit requirements IDs:

- Functional: F1–F7
- Non-functional: NF1–NF8
- Tests: T1–T4
- Tooling: TOOL1–TOOL2

You will see comments like `# F6, NF8` in the code to show which parts implement
which requirements. A more complete mapping is in `docs/requirements.md`.

## Features

- Store quiz questions (MCQ and freeform) in a JSON file. (F2)
- Practice mode with weighted random selection, focusing on weaker questions. (F6)
- Test mode with fixed-size quizzes and result logging. (F7)
- Optional integration with OpenAI's Responses API to:
  - Generate new questions for a topic. (F3)
  - Evaluate freeform answers semantically. (F6)
- Deterministic offline fallback when no API key is configured. (NF8)
- Dev vs prod configuration via environment variables. (NF6)

## Installation and setup

1. **Create and activate a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Linux/macOS
   # .venv\Scripts\activate         # Windows PowerShell
