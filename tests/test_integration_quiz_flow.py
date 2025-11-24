"""
Small integration tests for the Interactive Learning Tool.

Goal:
- Exercise models + repository + QuizManager together in a realistic mini flow.
- Show that a practice round updates stats and that they persist to disk.

Requirements touched:
- FR-3 (data persistence)
- FR-4 (statistics are tracked)
- FR-6 (practice mode selection)
- NFR-2, NFR-6 (robustness & data integrity)
"""

from interactive_learning_tool.models import Question
from interactive_learning_tool.repository import QuestionRepository
from interactive_learning_tool.quiz_manager import QuizManager


class DummyLLM:
    """
    Minimal stand-in for LLMClient.

    For this integration test we only need QuizManager's selection logic,
    so we don't call the LLM at all.
    """
    pass


def test_practice_round_updates_stats_and_persists(tmp_path):
    """
    End-to-end flow:

    1. Create a repository using a temporary questions.json.
    2. Add a single question and save it.
    3. Reload the repository and construct a QuizManager.
    4. Run one "practice round": choose a question, mark it correct, save.
    5. Reload again and verify shown/correct counters are persisted.

    This tests multiple components together: models, repository, quiz manager.
    """
    # 1) Create repo with a temp file
    questions_file = tmp_path / "questions.json"
    repo = QuestionRepository(path=questions_file)

    # 2) Add a single question and save
    q = Question(
        id=0,  # will be set by repo.add()
        topic="Python basics",
        text="What is the type of 42?",
        qtype="freeform",
        source="Manual",
    )
    repo.add(q)
    repo.save()

    # 3) Reload repository and create QuizManager
    repo2 = QuestionRepository(path=questions_file)
    repo2.load()
    qm = QuizManager(repo2, DummyLLM())

    # Sanity check: there is exactly one active question
    active = repo2.active_questions()
    assert len(active) == 1
    question = qm.choose_practice_question()
    assert question in active

    # 4) Simulate user answering correctly and save updated stats
    question.record_answer(is_correct=True)
    repo2.save()

    # 5) Reload again and verify stats persisted
    repo3 = QuestionRepository(path=questions_file)
    repo3.load()
    loaded = repo3.questions[0]

    assert loaded.stats.shown == 1
    assert loaded.stats.correct == 1
