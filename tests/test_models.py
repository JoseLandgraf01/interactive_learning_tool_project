from __future__ import annotations

import pytest

from learning_tool.exceptions import QuestionValidationError
from learning_tool.models import (
    Question,
    QuestionSource,
    QuestionStats,
    QuestionType,
)


def test_question_stats_accuracy_and_record_result() -> None:
    stats = QuestionStats()
    assert stats.accuracy == 0.0

    stats.record_result(True)
    assert stats.times_shown == 1
    assert stats.times_correct == 1
    assert stats.accuracy == 1.0

    stats.record_result(False)
    assert stats.times_shown == 2
    assert stats.times_correct == 1
    assert stats.accuracy == 0.5


def test_mcq_question_validation() -> None:
    q = Question(
        id="q1",
        topic="Python",
        text="What is the output of 1 + 1?",
        question_type=QuestionType.MCQ,
        source=QuestionSource.MANUAL,
        options=["1", "2"],
        correct_option_index=1,
    )
    assert q.is_mcq()
    assert not q.is_freeform()


def test_invalid_mcq_missing_options_raises() -> None:
    with pytest.raises(QuestionValidationError):
        Question(
            id="q2",
            topic="Python",
            text="Broken MCQ",
            question_type=QuestionType.MCQ,
            source=QuestionSource.MANUAL,
            options=[],
            correct_option_index=0,
        )


def test_freeform_question_validation() -> None:
    q = Question(
        id="q3",
        topic="Python",
        text="Explain what a list is in Python.",
        question_type=QuestionType.FREEFORM,
        source=QuestionSource.MANUAL,
        reference_answer="A mutable ordered collection type.",
    )
    assert q.is_freeform()
    assert not q.is_mcq()
