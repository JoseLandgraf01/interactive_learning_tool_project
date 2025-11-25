from __future__ import annotations
from pathlib import Path
from learning_tool.models import Question, QuestionSource, QuestionType
from learning_tool.quiz_manager import QuizManager
from learning_tool.repository import QuestionRepository

from learning_tool.models import QuestionStats


def create_manager(tmp_path: Path) -> QuizManager:
    path = tmp_path / "questions.json"
    repo = QuestionRepository(path=path)

    q1 = Question(
        id="q1",
        topic="Python",
        text="Explain what a variable is.",
        question_type=QuestionType.FREEFORM,
        source=QuestionSource.MANUAL,
        reference_answer="A named reference to a value in memory.",
    )
    q2 = Question(
        id="q2",
        topic="Python",
        text="What is the output of 2 * 3?",
        question_type=QuestionType.MCQ,
        source=QuestionSource.MANUAL,
        options=["4", "5", "6"],
        correct_option_index=2,
    )

    repo.save_all([q1, q2])
    return QuizManager(repository=repo)


def test_get_active_questions(tmp_path: Path) -> None:
    manager = create_manager(tmp_path)
    active = manager.get_active_questions()
    assert len(active) == 2

    manager.set_question_active("q1", False)
    active_after = manager.get_active_questions()
    assert len(active_after) == 1
    assert active_after[0].id == "q2"


def test_select_for_test_respects_count(tmp_path: Path) -> None:
    manager = create_manager(tmp_path)
    selected = manager.select_for_test(2)
    assert len(selected) == 2
    ids = {q.id for q in selected}
    assert ids == {"q1", "q2"}


class _DummyRepository:
    """Very small in-memory repository used for testing QuizManager."""

    def __init__(self, questions: list[Question]) -> None:
        self._questions = questions

    def load_all(self) -> list[Question]:
        """Mimic QuestionRepository.load_all()."""
        return list(self._questions)


def _make_freeform_question(
    qid: str,
    times_shown: int,
    times_correct: int,
    active: bool = True,
) -> Question:
    """Helper to build a valid freeform Question with given stats."""
    stats = QuestionStats(times_shown=times_shown, times_correct=times_correct)
    return Question(
        id=qid,
        topic="Testing",
        text=f"Question {qid}",
        question_type=QuestionType.FREEFORM,
        source=QuestionSource.MANUAL,
        active=active,
        reference_answer="Some reference answer",
        stats=stats,
    )


def test_compute_weight_prefers_weaker_questions() -> None:
    """
    F6: Weighted selection should give higher weight to questions
    with lower accuracy than to strong ones.
    """
    manager = QuizManager(repository=_DummyRepository([]))

    new_q = _make_freeform_question("new", times_shown=0, times_correct=0)
    weak_q = _make_freeform_question("weak", times_shown=10, times_correct=2)   # 20% accuracy
    strong_q = _make_freeform_question("strong", times_shown=10, times_correct=9)  # 90% accuracy

    w_new = manager._compute_weight(new_q)
    w_weak = manager._compute_weight(weak_q)
    w_strong = manager._compute_weight(strong_q)

    # We don’t assert exact numbers, only relative ordering.
    assert w_weak > w_strong
    # “Never seen” questions should not have the lowest priority.
    assert w_new >= w_strong


def test_select_for_practice_returns_only_active_questions() -> None:
    """
    F6 + F5: Practice mode should only serve active questions.
    """
    q1 = _make_freeform_question("q1", times_shown=5, times_correct=1, active=True)
    q2 = _make_freeform_question("q2", times_shown=3, times_correct=2, active=False)
    q3 = _make_freeform_question("q3", times_shown=0, times_correct=0, active=True)

    repo = _DummyRepository([q1, q2, q3])
    manager = QuizManager(repository=repo)

    # Call practice selection several times to be robust against randomness.
    for _ in range(20):
        selected = manager.select_for_practice()

        # We should always get a single Question instance...
        assert isinstance(selected, Question)

        # ...and it must always be active.
        assert selected.active

        # The inactive question must never be selected.
        assert selected is not q2
