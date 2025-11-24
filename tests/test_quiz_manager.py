"""
Tests for interactive_learning_tool.quiz_manager.QuizManager.

Goals:
- Verify the weighting heuristic for practice (FR-6).
- Verify error handling when there are no active questions (NFR-2).
- Verify test selection behaviour (FR-7, NFR-9).
"""

import pytest

from interactive_learning_tool.quiz_manager import QuizManager
from interactive_learning_tool.models import Question


class DummyRepo:
    """
    Minimal fake repository for QuizManager tests.

    It only implements active_questions(), which is all QuizManager needs.
    """

    def __init__(self, questions):
        self._questions = questions

    def active_questions(self):
        return [q for q in self._questions if q.active]


class DummyLLM:
    """Placeholder – QuizManager doesn't call the LLM directly in the methods we test."""
    pass


def _make_question(qid: int, shown: int, correct: int, active: bool = True) -> Question:
    """
    Helper to create a Question with specific stats.
    """
    q = Question(
        id=qid,
        topic="T",
        text=f"Q{qid}",
        qtype="freeform",
        source="Manual",
        active=active,
    )
    q.stats.shown = shown
    q.stats.correct = correct
    return q


def test_weight_unseen_question_is_highest():
    """
    Unseen questions (shown == 0) should get a higher weight than questions
    that have already been answered correctly.

    This is what makes practice mode "adaptive" in a simple way.

    Requirements:
        - FR-6 Practice Mode (Adaptive)
    """
    q_unseen = _make_question(1, shown=0, correct=0)
    q_good = _make_question(2, shown=10, correct=10)

    repo = DummyRepo([q_unseen, q_good])
    qm = QuizManager(repo, DummyLLM())

    w_unseen = qm._weight_for_question(q_unseen)
    w_good = qm._weight_for_question(q_good)

    assert w_unseen > w_good  # unseen questions get more attention


def test_choose_practice_question_raises_if_no_active():
    """
    If there are no active questions, practice mode should clearly signal
    the problem instead of silently failing.

    Requirements:
        - FR-6 Practice Mode
        - NFR-2 Robustness
    """
    repo = DummyRepo([])  # no questions at all
    qm = QuizManager(repo, DummyLLM())

    with pytest.raises(RuntimeError):
        qm.choose_practice_question()


def test_choose_test_questions_raises_if_not_enough_questions():
    """
    Requesting more test questions than are active should raise a ValueError.

    Requirements:
        - FR-7 Test Mode
        - NFR-2 Robustness
    """
    q1 = _make_question(1, shown=0, correct=0, active=True)
    repo = DummyRepo([q1])
    qm = QuizManager(repo, DummyLLM())

    with pytest.raises(ValueError):
        qm.choose_test_questions(count=2)  # only 1 question available


def test_choose_test_questions_returns_distinct_questions():
    """
    Test mode should return 'count' distinct questions (no repetition) when
    enough active questions are available.

    Requirements:
        - FR-7 Test Mode (random selection without repetition)
        - NFR-9 Extensibility (behaviour well-specified and test-protected)
    """
    q1 = _make_question(1, shown=0, correct=0, active=True)
    q2 = _make_question(2, shown=0, correct=0, active=True)
    q3 = _make_question(3, shown=0, correct=0, active=True)

    repo = DummyRepo([q1, q2, q3])
    qm = QuizManager(repo, DummyLLM())

    selected = qm.choose_test_questions(count=2)

    assert len(selected) == 2
    # Use object identity (id()) to be sure they are different instances
    assert id(selected[0]) != id(selected[1])
    assert all(q.active for q in selected)
