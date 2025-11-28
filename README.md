# Interactive Learning Tool – AI-Powered Learning Companion

This project implements an **AI-powered learning companion** that helps you:

- generate study questions with an LLM,
- practice and test your knowledge,
- track per-question statistics over time.

It is built as a **terminal application** with a strong focus on:

- clean, testable Python code (OOP, type hints),
- safe and predictable LLM usage,
- professional tooling (pytest, mypy, Ruff).

---

## Features

### User modes

1. **Generate Questions (LLM or fallback)**  
   - Enter a topic (e.g. “Python dictionaries”, “Linear regression basics”).  
   - The tool calls OpenAI to generate a mix of **MCQ** and **freeform** questions.  
   - You can review, edit, accept, or skip each question before it is saved.

2. **Practice Mode**  
   - Shows **active** questions one by one.  
   - MCQs are graded locally.  
   - Freeform answers are graded by the LLM based on a reference answer.  
   - Questions you miss become more likely to appear again (weighted random).

3. **Test Mode**  
   - Choose how many questions you want in a test.  
   - Questions are drawn randomly from active questions **without repetition**.  
   - Freeform answers are evaluated by the LLM, MCQs locally.  
   - A final score is shown and also appended to `results.txt`.

4. **Statistics Viewing**  
   - Shows each question’s:
     - ID (prefix),
     - Active flag,
     - Type (MCQ / freeform),
     - Topic,
     - Times shown,
     - Correct count,
     - Accuracy (%).

5. **Manage Questions (Enable/Disable)**  
   - Toggle a question’s active status by ID (or ID prefix).  
   - Disabled questions are never selected in Practice or Test mode.

---

## Architecture Overview

The project is organised as a small, testable package:

- `learning_tool/models.py`  
  - `QuestionType` (enum: `MCQ` / `FREEFORM`)  
  - `QuestionSource` (enum: `LLM` / `MANUAL`)  
  - `QuestionStats` (times shown, times correct, `accuracy` property)  
  - `Question` (question text, topic, options, reference answer, stats, etc.)

- `learning_tool/repository.py`  
  - `QuestionRepository`  
    - Persists questions to `questions.json` (JSON file).  
    - Handles loading/saving and simple validation.

- `learning_tool/quiz_manager.py`  
  - `QuestionRepositoryProtocol` – a `Protocol` describing the minimum repo interface.  
  - `QuizManager` – core quiz logic:
    - loads all questions at startup,
    - computes selection weights based on past accuracy,
    - chooses questions for practice / test,
    - updates statistics and persists changes.

- `learning_tool/llm_client.py`  
  - `GeneratedQuestionSpec` – lightweight structure for newly generated questions.  
  - `LLMClient` – wrapper around OpenAI with:
    - prompt templates from `prompts.py`,
    - rate limiting and retry logic,
    - strict JSON parsing and validation,
    - offline fallbacks when the API/key is unavailable.

- `learning_tool/prompts.py`  
  - Holds the only messages ever sent to the LLM:
    - `GEN_QUESTIONS_INSTRUCTIONS`,
    - `EVAL_FREEFORM_INSTRUCTIONS`.  
  - This makes the prompts easy to review, test, and evolve.

- `learning_tool/cli.py` and `main.py`  
  - `main.py` displays the menu and dispatches actions.  
  - `cli.py` contains the input/output workflow for each menu option.

- `tests/`  
  - Unit tests for models, repository, quiz logic, and LLM behaviour.  
  - LLM tests stub the OpenAI client so the test suite runs without network calls.

---

## LLM Integration

### Prompt design

All system-level instructions are centralised in `prompts.py`. They are:

- short and explicit, to reduce hallucinations,
- focused on **JSON output only**, so Python can parse the results,
- beginner-friendly and pedagogic (simple language, clear expectations).

For question generation, we ask for output shaped like:

```json
{
  "mcq": [
    {
      "question": "What is Python?",
      "options": ["A snake", "A programming language"],
      "correct_index": 1
    }
  ],
  "freeform": [
    {
      "question": "Explain what a list is in Python.",
      "reference_answer": "An ordered, mutable collection of items."
    }
  ]
}
```

For freeform evaluation, we request:

```json
{ "correct": true, "explanation": "short reasoning here" }
```

The code **never trusts the LLM blindly** – it validates the shape and content before using it.

### Error handling, retry, and rate limiting

All LLM calls go through `LLMClient`:

- `generate_questions(topic, num_questions)`
- `evaluate_freeform(question_text, reference_answer, user_answer)`

Internally:

- `_respect_rate_limit()` ensures at least 1 second between calls.
- `_call_with_retry()` retries on typical transient HTTP errors (429 / 5xx) with exponential backoff and jitter.
- Any failure is wrapped in a custom `LLMError` with clear user-facing messages.

### Fallback behaviour

If `OPENAI_API_KEY` is not set:

- In `dev` environment the app falls back to:
  - a built-in generic MCQ about the topic,
  - several simple freeform questions.
- In `prod` environment the same fallback is used, but a warning is logged.

For freeform evaluation, if no LLM is available, a simple **word-overlap heuristic** compares the user answer to the reference answer and returns a correctness guess plus explanation.

This design means the project can run on any machine (offline mode) while using OpenAI when available.

---

## Data Persistence

- **Questions**: stored in `questions.json` (JSON format).  
  JSON was chosen over CSV because:
  - questions have a nested structure (options list, stats object),
  - JSON is easier to evolve without breaking existing data,
  - it maps directly to Python dicts and lists.

- **Test results**: appended to `results.txt`.  
  Each line contains timestamp, number of questions, number correct, and percentage.

---

## Installation and Setup

### Prerequisites

- Python **3.11**
- Git

### 1. Clone the repository

```bash
git clone <this-repo-url>
cd interactive_learning_tool_project
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scriptsctivate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Set your OpenAI API key:

```bash
# PowerShell
$env:OPENAI_API_KEY = "sk-..."

# bash
export OPENAI_API_KEY="sk-..."
```

Optional environment flag:

```bash
# "dev" (default) or "prod"
$env:LEARNING_TOOL_ENV = "dev"
```

- With an API key set, the app uses the **real LLM**.
- Without a key, the app runs entirely in **fallback mode** (no network calls).

---

## Running the Application

From the project root, with the virtual environment activated:

```bash
python main.py
```

You should see:

```text
Welcome to the Learning Tool!
Environment: dev

Main menu
---------
1. Generate questions (LLM or fallback)  [F3]
2. Practice mode                         [F6]
3. Test mode                             [F7]
4. View question statistics              [F4]
5. Manage questions (enable/disable)     [F5]
0. Exit
```

### 1. Generate Questions

1. Choose `1` from the menu.  
2. Enter a topic, for example `Python dictionaries`.  
3. Choose how many questions to generate (default: 3).  
4. For each proposed question you can:
   - `a` – accept  
   - `s` – skip  
   - `e` – edit text / reference answer  
   - `q` – quit question review  
5. Accepted questions are converted into `Question` objects and persisted via `QuestionRepository`.

### 2. Practice Mode

1. Choose `2` from the menu.  
2. The tool selects an active question using weighted random logic:
   - if a question has never been shown → weight `1.0`,
   - otherwise → `weight = max(1.0 - accuracy, 0.1)`  
     (lower accuracy ⇒ higher weight, perfect accuracy ⇒ small but non-zero probability).
3. MCQ:
   - You choose an option (1, 2, 3, …).
   - Correctness is computed locally.
4. Freeform:
   - You type your answer.
   - The LLM compares it with the stored reference answer and returns `correct` and an explanation.
5. Statistics are updated and persisted after each answer.

### 3. Test Mode

1. Choose `3` from the menu.  
2. Enter how many questions you want in the test.  
3. Questions are drawn randomly from active questions, without repetition.  
4. Scoring and evaluation works as in practice mode.  
5. At the end, the app prints:

   ```text
   Your score: 7 / 10 (70%)
   ```

6. The score with date and time is appended to `results.txt`.

### 4. View Question Statistics

Shows a table like:

```text
ID       Act Type     Topic           Shown Correct Acc
-------------------------------------------------------
de4183c0 Y   mcq      Real Madrid         2       2 100%
764972e2 Y   freeform Trump               1       1 100%
...
```

- **ID** – question ID prefix (full ID is stored in JSON).  
- **Act** – active flag (`Y` / `N`).  
- **Acc** – accuracy percentage or `--` if the question has never been shown.

### 5. Manage Questions (Enable/Disable)

1. Choose `5` from the menu.  
2. You see all questions with their IDs and topics.  
3. Enter a full ID or ID prefix to toggle active status.  
4. The change is persisted to `questions.json`.

---

## Quality and Tooling

### Testing

The test suite uses **pytest** and covers:

- `tests/test_models.py` – `Question`, statistics, validation.  
- `tests/test_repository.py` – loading/saving JSON, persistence errors.  
- `tests/test_quiz_manager.py` – weighted selection, activation, toggling.  
- `tests/test_llm_client.py` – basic behaviour of `LLMClient`.  
- `tests/test_llm_client_validation.py` – strict validation of generated questions and evaluation JSON.

LLM tests use a stubbed OpenAI client so tests are deterministic and never hit the real API.

Run tests:

```bash
pytest
# or quieter:
pytest -q
```

### Static analysis

- **Ruff** – style and linting (PEP8, import order, common bugs):

  ```bash
  ruff check learning_tool tests
  ```

- **mypy** – static type checking:

  ```bash
  mypy learning_tool tests
  ```

Configuration for both tools lives in `pyproject.toml`.

---

## Design Notes (for Reviewers)

- **OOP structure**  
  - `Question` encapsulates all data and statistics and exposes methods like `record_result`.  
  - `QuestionRepository` handles persistence; `QuizManager` handles quiz logic.  
    This separation makes unit testing and future refactors easier.  
  - `LLMClient` isolates everything related to OpenAI (prompts, rate limit, retry, parsing).

- **Why JSON for questions instead of CSV?**  
  - Questions contain nested structures (lists, stats objects).  
  - JSON avoids awkward CSV encoding (e.g. commas inside text, options lists).  
  - Adding new fields later is easier and more robust.

- **Prompt robustness**  
  - All prompts are in `prompts.py`, making them easy to audit.  
  - They explicitly require JSON and avoid conversational fluff.  
  - The code validates the JSON shape and ignores malformed entries.

- **Security**  
  - API keys are never hard-coded.  
  - `OPENAI_API_KEY` is read from the environment.  
  - The project expects that `.venv` and any `.env` file are ignored by Git.

- **Offline / fallback behaviour**  
  - Without a key or on API failure, the tool still works with built-in questions and a simple heuristic checker.  
  - This makes it suitable for environments where network access is restricted.

---

## Possible Extensions

If this project were extended beyond the sprint, natural next steps would be:

- more advanced spaced repetition (e.g. SM-2 style scheduling),
- tagging questions by difficulty and sub-topic,
- export/import of question sets between machines,
- a simple web UI on top of the same core package e.g., using Claude/Tailwinds,
- richer evaluation feedback from the LLM (hints, follow-up questions).

---

## Previous Sprint Project

The previous project is **“dndgame-professional-python”**.  
You can find my earlier work on GitHub here:

- <https://github.com/JoseLandgraf01>
