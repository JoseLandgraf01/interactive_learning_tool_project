from __future__ import annotations


import pytest

from learning_tool.llm_client import LLMClient, GeneratedQuestionSpec
from learning_tool.models import QuestionType


def _clear_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Helper to ensure the fallback path is used in tests."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # We explicitly set env to "dev" to avoid prod warnings in tests.
    monkeypatch.setenv("LEARNING_TOOL_ENV", "dev")


def test_llm_client_is_unavailable_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """F3: LLMClient should report not available when no API key is set."""
    _clear_api_key_env(monkeypatch)

    client = LLMClient()

    assert client.is_available is False


def test_llm_client_is_available_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """F3: LLMClient should be available when an API key is present."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LEARNING_TOOL_ENV", "prod")

    client = LLMClient()

    assert client.is_available is True


def test_generate_questions_fallback_shapes_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    F3 + NF8:

    When no API key is configured, LLMClient should still return a reasonable
    list of GeneratedQuestionSpec objects using its fallback implementation.
    """
    _clear_api_key_env(monkeypatch)
    client = LLMClient()

    specs = client.generate_questions(topic="Python basics", num_questions=3)

    # At least one question should be generated.
    assert len(specs) >= 1

    for spec in specs:
        # All specs should have non-empty text and a valid question type.
        assert isinstance(spec, GeneratedQuestionSpec)
        assert isinstance(spec.text, str) and spec.text.strip()
        assert spec.question_type in {QuestionType.MCQ, QuestionType.FREEFORM}

        if spec.question_type is QuestionType.MCQ:
            # MCQ: should have options and a valid correct index.
            assert spec.options is not None and len(spec.options) >= 2
            assert spec.correct_option_index is not None
            assert 0 <= spec.correct_option_index < len(spec.options)
            # Freeform-specific fields should be empty.
            assert spec.reference_answer is None
        else:
            # FREEFORM: should have a reference answer and no options.
            assert spec.reference_answer is not None and spec.reference_answer.strip()
            assert spec.options is None or len(spec.options) == 0
            assert spec.correct_option_index is None
