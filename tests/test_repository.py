from __future__ import annotations

from pathlib import Path

from learning_tool.models import Question, QuestionSource, QuestionType
from learning_tool.repository import QuestionRepository


def create_sample_questions() -> list[Question]:
    q1 = Question(
        id="q1",
        topic="Python",
        text="What is a list in Python?",
        question_type=QuestionType.FREEFORM,
        source=QuestionSource.MANUAL,
        reference_answer="A mutable ordered collection type.",
    )
    q2 = Question(
        id="q2",
        topic="Python",
        text="What is the output of 1 + 1?",
        question_type=QuestionType.MCQ,
        source=QuestionSource.MANUAL,
        options=["1", "2"],
        correct_option_index=1,
    )
    return [q1, q2]


def test_missing_file_returns_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "questions.json"
    repo = QuestionRepository(path=path)
    assert repo.load_all() == []


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "questions.json"
    repo = QuestionRepository(path=path)

    original = create_sample_questions()
    repo.save_all(original)

    repo2 = QuestionRepository(path=path)
    loaded = repo2.load_all()

    assert len(loaded) == len(original)
    by_id = {q.id: q for q in loaded}
    assert by_id["q1"].topic == "Python"
    assert by_id["q1"].is_freeform()
    assert by_id["q2"].is_mcq()
