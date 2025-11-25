from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import json
import logging
import os

from learning_tool.exceptions import LLMError
from learning_tool.models import QuestionType
from openai import OpenAI  # external dependency; stubs come from the package

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
            self._client = OpenAI(api_key=api_key)


    @property
    def is_available(self) -> bool:
        """Return True if a real LLM client is configured and usable."""
        return self._client is not None

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
        """Call the OpenAI Responses API to generate questions.  # F3"""
        if self._client is None:  # pragma: no cover
            raise LLMError("LLM client is not configured.")

        instructions = (
            "You generate beginner-friendly study questions in JSON format. "
            "Return ONLY JSON, no extra text. The JSON must be a list of objects, "
            "each with: question_type ('mcq' or 'freeform'), text (string), "
            "options (list of strings, for 'mcq' only), correct_option_index (integer, "
            "for 'mcq' only), reference_answer (string, for 'freeform' only)."
        )
        prompt = (
            f"Create {num_questions} simple questions to help a beginner learn about: {topic}. "
            "Include at least one multiple-choice question and one freeform question."
        )

        try:  # pragma: no cover
            response = self._client.responses.create(
                model=self.model,
                instructions=instructions,
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

        if not isinstance(data, list):
            raise LLMError("Expected a JSON list of question objects from LLM.")

        specs: List[GeneratedQuestionSpec] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            qtype_str = str(item.get("question_type", "freeform")).lower()
            qtype = QuestionType.MCQ if qtype_str == "mcq" else QuestionType.FREEFORM
            text = str(item.get("text", "")).strip()
            if not text:
                continue

            options = item.get("options") if qtype is QuestionType.MCQ else None
            if isinstance(options, list):
                options = [str(opt) for opt in options]
            else:
                options = None

            correct_index = item.get("correct_option_index")
            if qtype is QuestionType.MCQ and not isinstance(correct_index, int):
                correct_index = 0

            reference_answer = (
                str(item.get("reference_answer", "")).strip()
                if qtype is QuestionType.FREEFORM
                else None
            )

            specs.append(
                GeneratedQuestionSpec(
                    question_type=qtype,
                    text=text,
                    options=options,
                    correct_option_index=correct_index,
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
        """Call the OpenAI Responses API to grade a freeform answer.  # F6"""
        if self._client is None:  # pragma: no cover
            raise LLMError("LLM client is not configured.")

        instructions = (
            "You are a strict but fair grader for short-answer questions. "
            "Return ONLY JSON, with keys 'is_correct' (true/false) and "
            "'explanation' (string). Consider semantic meaning, not just exact words."
        )
        prompt = (
            f"Question: {question_text}\n"
            f"Reference answer: {reference_answer}\n"
            f"Student answer: {user_answer}\n"
        )

        try:  # pragma: no cover
            response = self._client.responses.create(
                model=self.model,
                instructions=instructions,
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

        is_correct = bool(data.get("is_correct", False))
        explanation = str(data.get("explanation", "")).strip() or "No explanation provided."
        return is_correct, explanation
