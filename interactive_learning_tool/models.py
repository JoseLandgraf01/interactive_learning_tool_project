from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal


QuestionType = Literal["mcq", "freeform"]


@dataclass
class Stats:
    """Simple container for question statistics.

    Demonstrates:
        - Instance variables
        - @property
        - Operator overloading (__add__)

    Requirements:
        - FR-4: Statistics view
        - NFR-6: Data integrity
    """

    shown: int = 0
    correct: int = 0

    def __add__(self, other: "Stats") -> "Stats":
        if not isinstance(other, Stats):
            raise TypeError("Can only add Stats to Stats")
        return Stats(self.shown + other.shown, self.correct + other.correct)

    @property
    def accuracy(self) -> float:
        if self.shown == 0:
            return 0.0
        return self.correct / self.shown


@dataclass
class Question:
    """Base question model.

    Requirements:
        - FR-2, FR-3, FR-4, FR-6, FR-7, FR-8
        - NFR-4
    """

    id: int
    topic: str
    text: str
    qtype: QuestionType
    source: str = "LLM"
    active: bool = True
    stats: Stats = field(default_factory=Stats)

    def record_answer(self, is_correct: bool) -> None:
        self.stats.shown += 1
        if is_correct:
            self.stats.correct += 1

    def __str__(self) -> str:
        return f"[{self.id}] ({self.qtype}) {self.text}"


@dataclass
class MCQQuestion(Question):
    options: List[str] = field(default_factory=list)
    correct_index: int = 0

    def is_correct(self, choice_index: int) -> bool:
        """Return True if the given index matches the correct index."""
        return choice_index == self.correct_index


@dataclass
class FreeformQuestion(Question):
    reference_answer: str = """"""


def question_from_dict(data: Dict[str, Any]) -> Question:
    """Create a Question (MCQ or Freeform) from a plain dict."""
    qtype: QuestionType = data["qtype"]
    base_kwargs = {
        "id": data["id"],
        "topic": data["topic"],
        "text": data["text"],
        "qtype": qtype,
        "source": data.get("source", "LLM"),
        "active": data.get("active", True),
        "stats": Stats(
            shown=data.get("times_shown", 0),
            correct=data.get("times_correct", 0),
        ),
    }
    if qtype == "mcq":
        return MCQQuestion(
            options=data.get("options", []),
            correct_index=data.get("correct_index", 0),
            **base_kwargs,
        )
    elif qtype == "freeform":
        return FreeformQuestion(
            reference_answer=data.get("reference_answer", ""),
            **base_kwargs,
        )
    else:
        raise ValueError(f"Unknown question type: {qtype}")


def question_to_dict(q: Question) -> Dict[str, Any]:
    """Convert a Question object to a plain dict suitable for JSON."""
    base = {
        "id": q.id,
        "topic": q.topic,
        "text": q.text,
        "qtype": q.qtype,
        "source": q.source,
        "active": q.active,
        "times_shown": q.stats.shown,
        "times_correct": q.stats.correct,
    }
    if isinstance(q, MCQQuestion):
        base.update(
            {
                "options": q.options,
                "correct_index": q.correct_index,
            }
        )
    elif isinstance(q, FreeformQuestion):
        base.update({"reference_answer": q.reference_answer})
    return base
