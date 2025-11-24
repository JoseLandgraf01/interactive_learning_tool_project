from interactive_learning_tool.models import Stats, Question, MCQQuestion


def test_stats_addition():
    a = Stats(shown=3, correct=2)
    b = Stats(shown=1, correct=1)
    c = a + b
    assert c.shown == 4
    assert c.correct == 3


def test_question_record_answer():
    q = Question(id=1, topic="Python", text="What is int?", qtype="freeform")
    q.record_answer(True)
    q.record_answer(False)
    assert q.stats.shown == 2
    assert q.stats.correct == 1


def test_mcq_is_correct():
    q = MCQQuestion(
        id=1,
        topic="Python",
        text="2+2?",
        qtype="mcq",
        options=["3", "4"],
        correct_index=1,
    )
    assert q.is_correct(1)
    assert not q.is_correct(0)
