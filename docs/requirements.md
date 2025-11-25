# Requirements Catalogue & Status

This document tracks the requirements for the **Learning Tool** project and
their current implementation / testing status.

Status legend:

- ✅ **Done (tested)** – Implemented and covered by automated tests.
- ✅ **Done (manual)** – Implemented, exercised manually only.
- ⚠️ **Partial** – Implemented but with gaps (e.g. missing tests or edge-cases).
- ⏳ **Planned** – Not implemented yet.

---

## 1. Functional Requirements (F*)

| ID  | Title                                              | Status             | Notes |
| --- | -------------------------------------------------- | ------------------ | ----- |
| F1  | CLI entrypoint and main menu                       | ✅ Done (manual)   | `main.py`, `learning_tool.cli.main()`. Provides main menu and routes to modes. No direct CLI tests; underlying logic is tested by unit tests below. |
| F2  | Question storage and persistence                   | ✅ Done (tested)   | Questions + stats stored in JSON. `Question`, `QuestionStats` (`models.py`), `QuestionRepository` (`repository.py`). Covered by tests **T1**, **T2**. |
| F3  | LLM integration for question generation / grading  | ✅ Done (tested)   | Implemented in `llm_client.LLMClient` with OpenAI Responses API + offline fallback. Fallback generation + availability covered by **T4** (`tests/test_llm_client.py`). Freeform grading logic is simple and validated manually via CLI. |
| F4  | View question statistics                           | ✅ Done (manual)   | Implemented in `cli.handle_view_statistics`. Uses stats from `QuestionStats`. No dedicated tests; relies on F2/T1/T2 for underlying correctness. |
| F5  | Manage questions (enable/disable)                  | ✅ Done (tested)   | Logic in `QuizManager.set_question_active`, `.toggle_question_active`, CLI in `handle_manage_questions`. Core active/inactive logic tested in **T3**. |
| F6  | Practice mode with weighted random selection       | ✅ Done (tested)   | Weighting logic in `QuizManager._compute_weight` and `select_for_practice`. Behaviour covered by **T3** (existing tests) plus additional tests in `tests/test_quiz_manager.py` that verify higher weight for weaker questions and only active questions being selected. |
| F7  | Test mode with fixed-size quiz & result logging    | ✅ Done (manual)   | Implemented in `cli.handle_test_mode`, using `QuizManager.select_for_test`. Uses `AppConfig.results_path` for logging. Manual testing only; selection logic partially covered by **T3**. |

---

## 2. Non-Functional Requirements (NF*)

| ID   | Title                                                     | Status             | Notes |
| ---- | --------------------------------------------------------- | ------------------ | ----- |
| NF1  | Clear separation of concerns (models / logic / CLI)       | ✅ Done (design)   | Package layout: `learning_tool.models`, `repository`, `quiz_manager`, `llm_client` vs `cli`. Supports readability and testing. |
| NF2  | LLM behind a small, testable wrapper                      | ✅ Done (tested)   | `LLMClient` encapsulates all OpenAI access + JSON parsing. Fallback behaviour and availability are tested in **T4**. CLI never talks to OpenAI directly. |
| NF3  | Validation and robust error handling                      | ✅ Done (tested)   | Custom exceptions in `exceptions.py` (`LearningToolError` + subclasses). Validation for `Question` enforced in `__post_init__`. Covered by **T1**; persistence errors handled in `QuestionRepository` and logged. |
| NF4  | CLI usability (clear prompts, safe handling of bad input) | ✅ Done (manual)   | CLI loops validate user input, provide error messages and allow cancellation. Manually exercised in both dev and prod modes. |
| NF5  | File path portability & data location control             | ✅ Done (design)   | `AppConfig` / `load_config` (`config.py`) configure `base_dir`, `questions_path`, `results_path` via env vars; uses `pathlib.Path` so paths are cross-platform. |
| NF6  | Dev vs prod behaviour, environment awareness               | ✅ Done (design)   | `AppConfig.env` driven by `LEARNING_TOOL_ENV`; `LLMClient` logs a warning in `prod` when API key is missing and falls back quietly in `dev`. |
| NF7  | Logging for debugging and observability                   | ✅ Done (design)   | `logging` used in `repository.py` and `llm_client.py`; logging configured in `main.py` (and/or `logger_config`). Log level controlled via `LEARNING_TOOL_LOG_LEVEL`. |
| NF8  | Deterministic offline / test mode (no API key required)   | ✅ Done (tested)   | Fallback implementations in `LLMClient._fallback_generate_questions` and `_fallback_evaluate`. Fallback generation path is covered by **T4**; CLI manually verified with no `OPENAI_API_KEY` set. |

---

## 3. Testing Requirements (T*)

| ID  | Title                                             | Status           | Notes |
| --- | ------------------------------------------------- | ---------------- | ----- |
| T1  | Unit tests for models & validation                | ✅ Done          | `tests/test_models.py` checks `QuestionStats`, `Question` validation (MCQ vs freeform, required fields, invalid combinations). |
| T2  | Unit tests for repository (JSON IO)               | ✅ Done          | `tests/test_repository.py` checks round-trip save/load, creation of storage file and missing file behaviour. |
| T3  | Unit tests for quiz manager (core logic & F6)     | ✅ Done          | `tests/test_quiz_manager.py` checks active filtering, `select_for_test`, weight computation, and that practice mode only serves active questions while preferring weaker ones. |
| T4  | Tests for LLM fallback and availability behaviour | ✅ Done          | `tests/test_llm_client.py` exercises `LLMClient` in fallback mode (no API key): availability, shape of generated questions, and MCQ vs freeform structure. |

---

## 4. Tooling Requirements (TOOL*)

| ID     | Title                           | Status           | Notes |
| ------ | --------------------------------| ---------------- | ----- |
| TOOL1  | Linting & formatting with ruff  | ✅ Done (config) | `pyproject.toml` contains `[tool.ruff]` config. Lint checks run via `ruff check learning_tool tests`. Current codebase passes with no issues. |
| TOOL2  | Static typing with mypy         | ✅ Done (config) | Types added across modules; `[tool.mypy]` section in `pyproject.toml` enables strict checking. Command: `mypy -p learning_tool --strict`. Current codebase passes with no type errors. |

---

## 5. Implementation Notes for Key Requirements

### F3 – LLM integration for question generation / grading

- Implemented in `learning_tool.llm_client.LLMClient`.
- Uses the OpenAI **Responses API** when `OPENAI_API_KEY` is set.
- Falls back to `_fallback_generate_questions` and `_fallback_evaluate` when no key is present, so the CLI remains usable in dev/test environments.
- `GeneratedQuestionSpec` acts as a small DTO between the LLM and the rest of the app.
- Tests in `tests/test_llm_client.py` verify:
  - behaviour with and without API key,
  - that fallback generation returns well-formed questions (MCQ + freeform).

Grading uses a simple heuristic in fallback mode and relies on OpenAI’s scoring otherwise. Because the LLM is non-deterministic, detailed grading behaviour is validated manually via the CLI.

### F6 – Practice mode with weighted random selection

- Implemented in `learning_tool.quiz_manager.QuizManager`:
  - `_compute_weight(question)` assigns higher weights to questions with **lower accuracy** and to never-seen questions.
  - `select_for_practice()` chooses a single question using the computed weights, but only among **active** questions.
- Additional tests in `tests/test_quiz_manager.py` check that:
  - weaker questions get higher weight than strong ones,
  - never-seen questions are not starved,
  - practice mode never returns an inactive question.

---

## 6. Traceability Cheat-Sheet

Quick mapping from requirement IDs to key modules and tests:

- **F1** → `main.py`, `learning_tool/cli.py`
- **F2** → `learning_tool/models.py`, `learning_tool/repository.py`, tests: **T1**, **T2**
- **F3** → `learning_tool/llm_client.py`, tests: **T4**
- **F4** → `learning_tool/cli.py` (`handle_view_statistics`)
- **F5** → `learning_tool/quiz_manager.py`, `learning_tool/cli.py` (`handle_manage_questions`), tests: **T3**
- **F6** → `learning_tool/quiz_manager.py` (`_compute_weight`, `select_for_practice`), tests: **T3**
- **F7** → `learning_tool/quiz_manager.py` (`select_for_test`), `learning_tool/cli.py` (`handle_test_mode`)
- **NF1–NF3** → `learning_tool/models.py`, `learning_tool/exceptions.py`, `learning_tool/repository.py`
- **NF4** → `learning_tool/cli.py`
- **NF5–NF6** → `learning_tool/config.py`, `learning_tool/llm_client.py`
- **NF7** → `main.py` / `logger_config.py`, `learning_tool/repository.py`, `learning_tool/llm_client.py`
- **NF8** → `learning_tool/llm_client.py`, tests: **T4**
- **TOOL1–TOOL2** → `pyproject.toml`

