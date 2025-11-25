from __future__ import annotations

from pathlib import Path

from learning_tool.models import Question, QuestionSource, QuestionType
from learning_tool.quiz_manager import QuizManager
from learning_tool.repository import QuestionRepository


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
