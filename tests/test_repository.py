"""
Tests for interactive_learning_tool.repository.QuestionRepository.

Goals:
- Verify JSON load/save behaviour (FR-3, NFR-2, NFR-6).
- Verify ID assignment and active question filtering (FR-5).
- Show robustness to missing/invalid files (NFR-2).
"""

from pathlib import Path
import json

from interactive_learning_tool.repository import QuestionRepository
from interactive_learning_tool.models import Question


def _make_repo(tmp_path) -> QuestionRepository:
    """
    Helper: create a repository that uses a temp file instead of the real data/questions.json.

    Using tmp_path means our tests don't touch your real data folder.
    """
    path = tmp_path / "questions.json"
    return QuestionRepository(path=path)


def test_load_missing_file_starts_empty(tmp_path):
    """
    If the questions file doesn't exist yet, load() should NOT crash and
    should leave the repository empty.

    Requirements:
        - NFR-2 Robustness
        - NFR-6 Data integrity
    """
    repo = _make_repo(tmp_path)
    # File does not exist yet.
    assert not repo.path.exists()

    repo.load()

    assert repo.questions == []  # no crash, just an empty list


def test_save_and_load_roundtrip(tmp_path):
    """
    Saving then loading should preserve question fields.

    This checks that question_to_dict / question_from_dict and
    repository.load/save are consistent with each other.

    Requirements:
        - FR-3 Data persistence
        - NFR-6 Data integrity
    """
    repo = _make_repo(tmp_path)

    # Create a simple freeform question
    q = Question(
        id=0,  # will be overwritten by repo.add()
        topic="Python basics",
        text="What is the type of 42?",
        qtype="freeform",
        source="Manual",
    )
    repo.add(q)
    repo.save()

    # New repository instance reading the same file
    repo2 = QuestionRepository(path=repo.path)
    repo2.load()
    questions = repo2.questions

    assert len(questions) == 1
    loaded = questions[0]

    # ID should have been auto-assigned by repo.add()
    assert loaded.id == 1
    assert loaded.topic == "Python basics"
    assert loaded.text == "What is the type of 42?"
    assert loaded.qtype == "freeform"
    assert loaded.source == "Manual"
    assert loaded.stats.shown == 0
    assert loaded.stats.correct == 0
    assert loaded.active is True


def test_active_questions_filters_inactive(tmp_path):
    """
    active_questions() should only return questions with active=True.

    Requirements:
        - FR-5 Manage questions
    """
    repo = _make_repo(tmp_path)
    # Manually inject questions into the repository
    q1 = Question(id=1, topic="T1", text="Q1", qtype="freeform", active=True)
    q2 = Question(id=2, topic="T2", text="Q2", qtype="freeform", active=False)
    repo._questions = [q1, q2]  # In tests it's OK to touch _questions directly

    active = repo.active_questions()

    assert active == [q1]
    assert q2 not in active


def test_load_invalid_json_recovers_gracefully(tmp_path):
    """
    If the JSON file is corrupted, load() should log an error but still
    leave the repository in a sane state (empty list), without raising
    a JSONDecodeError to the user.

    Requirements:
        - NFR-2 Robustness
        - NFR-6 Data integrity
    """
    path = tmp_path / "questions.json"
    # Write invalid JSON
    path.write_text("this is not valid json", encoding="utf-8")

    repo = QuestionRepository(path=path)
    # Should NOT raise JSONDecodeError
    repo.load()

    assert repo.questions == []  # falls back to empty
