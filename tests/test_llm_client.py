"""
Tests for interactive_learning_tool.llm_client.LLMClient (stub version).

Goals:
- Ensure the naive freeform evaluation behaves as documented.
- Ensure LLMClient initialises safely even without an API key set.

Requirements touched:
- FR-2 (LLM question generation - structure)
- FR-6 / FR-7 (freeform evaluation path)
- SEC-1 / SEC-2 (no hard crash if key is missing)
- NFR-2 (robustness)
"""

import os

from interactive_learning_tool.llm_client import LLMClient


def test_evaluate_freeform_correct_when_answers_match_ignoring_case_and_spaces():
    """
    The stub implementation compares answers with strip().lower().

    This test documents that behaviour explicitly so if we later change it
    (e.g. to a real LLM call), we know what we are changing.

    Requirements:
        - FR-6 / FR-7: correctness of freeform evaluation
    """
    client = LLMClient()

    is_correct, explanation = client.evaluate_freeform(
        question_text="What is the type of 42?",
        reference_answer=" int ",
        user_answer="INT",
    )

    assert is_correct is True
    assert "Naive evaluation" in explanation


def test_evaluate_freeform_false_for_different_answer():
    """
    When the student's answer is clearly different, the stub should return False.

    This is a simple regression test to protect the basic behaviour.
    """
    client = LLMClient()

    is_correct, explanation = client.evaluate_freeform(
        question_text="What is the type of 42?",
        reference_answer="int",
        user_answer="string",
    )

    assert is_correct is False
    assert "Naive evaluation" in explanation


def test_llmclient_initializes_without_api_key(monkeypatch):
    """
    LLMClient must not crash if OPENAI_API_KEY is not set.

    In the current design we log a warning but still construct the client.
    This test ensures that behaviour remains true.

    Requirements:
        - SEC-1 / SEC-2 (missing key is handled gracefully)
        - NFR-2 (robustness)
    """
    # Ensure the env var is unset for this test
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = LLMClient()  # Should not raise

    # For now, the stub has no real client, but we can at least check the model name
    assert isinstance(client.model, str)
