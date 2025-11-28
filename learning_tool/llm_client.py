from __future__ import annotations

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from learning_tool.exceptions import LLMError
from learning_tool.models import QuestionType
from openai import OpenAI  # external dependency; stubs come from the package

from .prompts import (
    EVAL_FREEFORM_INSTRUCTIONS,
    GEN_QUESTIONS_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQuestionSpec:
    """Lightweight representation of a newly generated question.  # F3"""

    question_type: QuestionType
    text: str
    options: Optional[List[str]] = None
    correct_option_index: Optional[int] = None
    reference_answer: Optional[str] = None


@dataclass
class LLMClient:
    """Wrapper around the OpenAI client with safe fallbacks.  # F3, F6, NF2, NF3, NF6, NF8"""

    model: str = "gpt-4.1-mini"
    timeout_seconds: int = 30
    _client: Any | None = None

    def __post_init__(self) -> None:
        """Initialise underlying OpenAI client or fall back if no API key is set."""
        api_key = os.getenv("OPENAI_API_KEY")
        env = os.getenv("LEARNING_TOOL_ENV", "dev").lower()

        if not api_key:
            # NF8: in dev we happily fall back; in prod we log a warning.
            if env == "prod":
                logger.warning("OPENAI_API_KEY missing in prod environment.")
            self._client = None
        else:
            # pass timeout into the OpenAI client
            self._client = OpenAI(api_key=api_key, timeout=self.timeout_seconds)

        # Simple client-side rate limiting & retry config
        self._last_call_ts: float = 0.0
        self._min_interval: float = 1.0  # seconds between calls
        self._max_attempts: int = 3

    @property
    def is_available(self) -> bool:
        """Return True if a real LLM client is configured and usable."""
        return self._client is not None

    # --- infrastructure helpers: rate limit + retry --------------------

    def _respect_rate_limit(self) -> None:
        """Ensure a minimum delay between API calls (very simple client-side rate limit)."""
        now = time.time()
        elapsed = now - self._last_call_ts
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_ts = time.time()

    def _call_with_retry(self, func, *args, **kwargs):
        """
        Call `func` with retries for transient HTTP errors.

        Retries for typical transient statuses (429 / 5xx) with exponential
        backoff and jitter. If the error is not transient or all attempts fail,
        the exception is re-raised for the caller to handle.
        """
        for attempt in range(1, self._max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover  (HTTP-level behaviour)
                status = getattr(exc, "status_code", None)
                transient = status in (429, 500, 502, 503)

                if not transient or attempt == self._max_attempts:
                    # Not transient or out of retries: let caller wrap in LLMError.
                    raise

                backoff = (2 ** (attempt - 1)) + random.random()
                logger.warning(
                    "Transient LLM error (status=%s, attempt=%s/%s): %s; "
                    "retrying in %.1fs",
                    status,
                    attempt,
                    self._max_attempts,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

    # --- public API -----------------------------------------------------

    def generate_questions(self, topic: str, num_questions: int = 3) -> List[GeneratedQuestionSpec]:
        """Generate a set of study questions for a topic.  # F3, NF8"""
        topic = topic.strip()
        if not topic:
            raise ValueError("Topic must not be empty.")
        if num_questions <= 0:
            raise ValueError("Number of questions must be positive.")

        if not self.is_available:
            return self._fallback_generate_questions(topic, num_questions)

        return self._llm_generate_questions(topic, num_questions)

    def evaluate_freeform(
        self,
        question_text: str,
        reference_answer: str,
        user_answer: str,
    ) -> Tuple[bool, str]:
        """Evaluate a freeform answer using LLM or heuristic.  # F6, NF8"""
        question_text = question_text.strip()
        reference_answer = reference_answer.strip()
        user_answer = user_answer.strip()

        if not question_text or not reference_answer:
            raise ValueError("Question text and reference answer must not be empty.")

        if not self.is_available:
            return self._fallback_evaluate(reference_answer, user_answer)

        return self._llm_evaluate(question_text, reference_answer, user_answer)

    # --- fallback implementations (no real LLM) ------------------------

    @staticmethod
    def _fallback_generate_questions(topic: str, num_questions: int) -> List[GeneratedQuestionSpec]:
        """Generate simple built-in questions without calling any API.  # NF8"""
        specs: List[GeneratedQuestionSpec] = []

        # One generic MCQ plus freeform questions.
        mcq = GeneratedQuestionSpec(
            question_type=QuestionType.MCQ,
            text=f"Which statement best describes {topic}?",
            options=[
                f"{topic} is a core concept in Python programming.",
                f"{topic} is a type of database engine.",
                f"{topic} is a graphical design tool.",
                f"{topic} is a brand of computer hardware.",
            ],
            correct_option_index=0,
        )
        specs.append(mcq)

        remaining = max(num_questions - 1, 0)
        for idx in range(remaining):
            specs.append(
                GeneratedQuestionSpec(
                    question_type=QuestionType.FREEFORM,
                    text=f"In your own words, explain what '{topic}' means (variation {idx + 1}).",
                    reference_answer=f"A clear, concise explanation of {topic}.",
                )
            )

        return specs

    @staticmethod
    def _fallback_evaluate(
        reference_answer: str,
        user_answer: str,
    ) -> Tuple[bool, str]:
        """Very simple heuristic based on word overlap.  # NF8"""
        ref_words = {w for w in reference_answer.lower().split() if len(w) > 3}
        user_words = {w for w in user_answer.lower().split() if len(w) > 3}

        if not ref_words:
            return False, "No reference words to compare against."

        overlap = ref_words & user_words
        ratio = len(overlap) / len(ref_words)

        is_correct = ratio >= 0.4
        explanation = (
            f"Overlap ratio {ratio:.2f} based on key words: "
            f"{', '.join(sorted(overlap)) if overlap else 'no significant matches'}."
        )
        return is_correct, explanation

    # --- real LLM-backed implementations -------------------------------

    def _llm_generate_questions(
        self,
        topic: str,
        num_questions: int,
    ) -> List[GeneratedQuestionSpec]:
        """
        Call the OpenAI Responses API to generate questions.  # F3

        Expects the LLM (guided by GEN_QUESTIONS_INSTRUCTIONS) to return JSON:

        {
          "mcq": [
            {"question": "...", "options": ["...","..."], "correct_index": 0},
            ...
          ],
          "freeform": [
            {"question": "...", "reference_answer": "..."},
            ...
          ]
        }
        """
        if self._client is None:  # pragma: no cover
            raise LLMError("LLM client is not configured.")

        self._respect_rate_limit()

        prompt = (
            f"Create {num_questions} beginner-friendly questions to help a student "
            f"learn about: {topic}. Include at least one multiple-choice question "
            f"and one freeform question. Use the JSON structure from the instructions."
        )

        try:  # pragma: no cover
            response = self._call_with_retry(
                self._client.responses.create,
                model=self.model,
                instructions=GEN_QUESTIONS_INSTRUCTIONS,
                input=prompt,
                max_output_tokens=800,
        )

        except Exception as exc:
            logger.exception("LLM call failed for question generation (topic=%s)", topic)
            raise LLMError("Failed calling LLM for question generation.") from exc

        raw_text = getattr(response, "output_text", None)
        if not raw_text:
            raise LLMError("LLM returned an empty response for question generation.")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.exception("Invalid JSON from LLM for question generation")
            raise LLMError("LLM did not return valid JSON for questions.") from exc

        if not isinstance(data, dict):
            raise LLMError("Expected a JSON object with 'mcq' and 'freeform' lists.")

        specs: List[GeneratedQuestionSpec] = []

        # Validate MCQs
        for item in data.get("mcq", []):
            if not isinstance(item, dict):
                continue

            text = str(item.get("question", "")).strip()
            if not text:
                continue

            raw_options = item.get("options", [])
            if not isinstance(raw_options, list) or len(raw_options) < 2:
                continue
            options = [str(opt) for opt in raw_options]

            correct_index = item.get("correct_index", 0)
            if not isinstance(correct_index, int) or not (0 <= correct_index < len(options)):
                correct_index = 0

            specs.append(
                GeneratedQuestionSpec(
                    question_type=QuestionType.MCQ,
                    text=text,
                    options=options,
                    correct_option_index=correct_index,
                )
            )

        # Validate freeform questions
        for item in data.get("freeform", []):
            if not isinstance(item, dict):
                continue

            text = str(item.get("question", "")).strip()
            reference_answer = str(item.get("reference_answer", "")).strip()
            if not text or not reference_answer:
                continue

            specs.append(
                GeneratedQuestionSpec(
                    question_type=QuestionType.FREEFORM,
                    text=text,
                    reference_answer=reference_answer,
                )
            )

        if not specs:
            raise LLMError("No usable questions were parsed from LLM response.")

        return specs

    def _llm_evaluate(
        self,
        question_text: str,
        reference_answer: str,
        user_answer: str,
    ) -> Tuple[bool, str]:
        """
        Call the OpenAI Responses API to grade a freeform answer.  # F6

        Expects JSON:

        { "correct": true/false, "explanation": "..." }

        but also accepts legacy `is_correct` for robustness.
        """
        if self._client is None:  # pragma: no cover
            raise LLMError("LLM client is not configured.")

        self._respect_rate_limit()

        prompt = (
            f"Question: {question_text}\n"
            f"Reference answer: {reference_answer}\n"
            f"Student answer: {user_answer}\n"
        )

        try:  # pragma: no cover
            response = self._call_with_retry(
                self._client.responses.create,
                model=self.model,
                instructions=EVAL_FREEFORM_INSTRUCTIONS,
                input=prompt,
                max_output_tokens=400,
        )

        except Exception as exc:
            logger.exception("LLM call failed for freeform evaluation")
            raise LLMError("Failed calling LLM for freeform evaluation.") from exc

        raw_text = getattr(response, "output_text", None)
        if not raw_text:
            raise LLMError("LLM returned an empty response for evaluation.")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.exception("Invalid JSON from LLM for evaluation")
            raise LLMError("LLM did not return valid JSON for evaluation.") from exc

        if not isinstance(data, dict):
            raise LLMError("Expected a JSON object from LLM evaluation.")

        # Prefer new schema { "correct": ... }, but accept legacy "is_correct"
        if "correct" in data:
            is_correct = bool(data["correct"])
        else:
            is_correct = bool(data.get("is_correct", False))

        explanation = str(data.get("explanation", "")).strip() or "No explanation provided."
        return is_correct, explanation
