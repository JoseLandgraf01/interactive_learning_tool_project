import json
from types import SimpleNamespace

import pytest
from learning_tool.exceptions import LLMError
from learning_tool.llm_client import GeneratedQuestionSpec, LLMClient
from learning_tool.models import QuestionType


class StubResponses:
    """
    Very small stub for the `.responses.create(...)` part of the OpenAI client.

    It always returns an object with an `output_text` attribute containing
    a JSON dump of the provided `json_obj`.
    """

    def __init__(self, json_obj):
        self._response = SimpleNamespace(output_text=json.dumps(json_obj))

    def create(self, **kwargs):
        # We ignore kwargs; this is enough for our tests.
        return self._response


def make_stubbed_client(monkeypatch, json_obj) -> LLMClient:
    """
    Create an LLMClient instance whose internal `_client` is replaced by a stub
    that returns `json_obj` as the JSON response.

    We also disable rate limiting and the retry wrapper so that the tests are
    fast and deterministic.
    """
    # Pretend we have an API key so __post_init__ doesn't put us in fallback mode.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = LLMClient()
    # Replace the real OpenAI client with our stub
    client._client = SimpleNamespace(responses=StubResponses(json_obj))  # type: ignore[attr-defined]
    # Disable rate limiting and retry logic for unit tests
    client._respect_rate_limit = lambda: None  # type: ignore[assignment]
    client._call_with_retry = lambda func, *args, **kwargs: func(**kwargs)  # type: ignore[assignment]
    return client


# ---------------------------------------------------------------------------
# Question generation validation tests
# ---------------------------------------------------------------------------


def test_llm_generate_questions_parses_valid_mcq_and_freeform(monkeypatch):
    """
    Happy-path test: valid MCQ and freeform entries are converted into
    GeneratedQuestionSpec objects with correct fields.
    """
    json_payload = {
        "mcq": [
            {
                "question": "What is Python?",
                "options": ["A snake", "A programming language"],
                "correct_index": 1,
            }
        ],
        "freeform": [
            {
                "question": "Explain what a list is in Python.",
                "reference_answer": "An ordered, mutable collection of items.",
            }
        ],
    }

    client = make_stubbed_client(monkeypatch, json_payload)
    specs = client._llm_generate_questions("Python", num_questions=2)

    # We expect exactly two questions: one MCQ and one freeform.
    assert len(specs) == 2
    assert any(s.question_type is QuestionType.MCQ for s in specs)
    assert any(s.question_type is QuestionType.FREEFORM for s in specs)

    mcq = next(s for s in specs if s.question_type is QuestionType.MCQ)
    assert isinstance(mcq, GeneratedQuestionSpec)
    assert mcq.options == ["A snake", "A programming language"]
    assert mcq.correct_option_index == 1

    free = next(s for s in specs if s.question_type is QuestionType.FREEFORM)
    assert free.reference_answer == "An ordered, mutable collection of items."


def test_llm_generate_questions_filters_out_invalid_items(monkeypatch):
    """
    Only structurally valid questions should become GeneratedQuestionSpec
    instances. Invalid entries are silently dropped.
    """
    json_payload = {
        "mcq": [
            # Invalid: less than 2 options -> should be dropped
            {
                "question": "Broken MCQ",
                "options": ["only one option"],
                "correct_index": 0,
            },
            # Valid MCQ
            {
                "question": "Valid MCQ?",
                "options": ["no", "yes"],
                "correct_index": 1,
            },
        ],
        "freeform": [
            # Invalid: missing reference_answer -> dropped
            {
                "question": "What is invalid here?",
                "reference_answer": "",
            },
            # Valid freeform
            {
                "question": "Valid freeform?",
                "reference_answer": "Some explanation.",
            },
        ],
    }

    client = make_stubbed_client(monkeypatch, json_payload)
    specs = client._llm_generate_questions("Some topic", num_questions=4)

    # We expect only the two valid questions.
    assert len(specs) == 2
    assert any(s.question_type is QuestionType.MCQ for s in specs)
    assert any(s.question_type is QuestionType.FREEFORM for s in specs)


def test_llm_generate_questions_raises_if_all_items_invalid(monkeypatch):
    """
    If every entry in the JSON payload is invalid, _llm_generate_questions
    should raise LLMError rather than returning an empty list.
    """
    json_payload = {
        "mcq": [
            {
                "question": "",
                "options": [],
                "correct_index": 0,
            }
        ],
        "freeform": [
            {
                "question": "",
                "reference_answer": "",
            }
        ],
    }

    client = make_stubbed_client(monkeypatch, json_payload)
    with pytest.raises(LLMError):
        client._llm_generate_questions("Broken topic", num_questions=2)


# ---------------------------------------------------------------------------
# Freeform evaluation validation tests
# ---------------------------------------------------------------------------


def test_llm_evaluate_uses_correct_field_and_explanation(monkeypatch):
    """
    When the LLM returns {"correct": true, "explanation": "..."} the
    _llm_evaluate helper must convert it into (True, explanation).
    """
    json_payload = {"correct": True, "explanation": "Looks good."}

    client = make_stubbed_client(monkeypatch, json_payload)
    is_correct, explanation = client._llm_evaluate(
        question_text="Q?",
        reference_answer="Ref",
        user_answer="User",
    )

    assert is_correct is True
    assert explanation == "Looks good."


def test_llm_evaluate_accepts_legacy_is_correct_key(monkeypatch):
    """
    For robustness, if the LLM returns 'is_correct' instead of 'correct',
    we still interpret it properly and provide a default explanation.
    """
    json_payload = {"is_correct": False}

    client = make_stubbed_client(monkeypatch, json_payload)
    is_correct, explanation = client._llm_evaluate(
        question_text="Q?",
        reference_answer="Ref",
        user_answer="User",
    )

    assert is_correct is False
    assert explanation == "No explanation provided."
