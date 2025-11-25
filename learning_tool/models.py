from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from .exceptions import QuestionValidationError


class QuestionType(str, Enum):
    """Type of question presented to the user.  # F2"""

    MCQ = "mcq"
    FREEFORM = "freeform"


class QuestionSource(str, Enum):
    """Where this question came from.  # F2"""

    LLM = "llm"
    MANUAL = "manual"


@dataclass
class QuestionStats:
    """Track how often a question is shown and answered correctly.  # F2, T1, NF3"""

    times_shown: int = 0
    times_correct: int = 0

    def record_result(self, is_correct: bool) -> None:
        """Update statistics after an answer."""
        self.times_shown += 1
        if is_correct:
            self.times_correct += 1

    @property
    def accuracy(self) -> float:
        """Return ratio of correct answers, or 0.0 if never shown."""
        if self.times_shown == 0:
            return 0.0
        return self.times_correct / self.times_shown


@dataclass
class Question:
    """Represent a single quiz question.  # F2, NF1, NF3"""

    id: str
    topic: str
    text: str
    question_type: QuestionType
    source: QuestionSource
    active: bool = True
    options: List[str] = field(default_factory=list)
    correct_option_index: Optional[int] = None
    reference_answer: Optional[str] = None
    stats: QuestionStats = field(default_factory=QuestionStats)

    def __post_init__(self) -> None:
        """Validate internal consistency after initialization.  # NF3, T1"""
        if self.question_type is QuestionType.MCQ:
            if not self.options:
                raise QuestionValidationError(
                    "MCQ question must have at least one option."
                )
            if self.correct_option_index is None:
                raise QuestionValidationError(
                    "MCQ question must define correct_option_index."
                )
            if not (0 <= self.correct_option_index < len(self.options)):
                raise QuestionValidationError(
                    "correct_option_index is out of range for options."
                )
            if self.reference_answer is not None:
                raise QuestionValidationError(
                    "MCQ question should not define reference_answer."
                )

        elif self.question_type is QuestionType.FREEFORM:
            if self.reference_answer is None:
                raise QuestionValidationError(
                    "Freeform question must define reference_answer."
                )
            if self.options or self.correct_option_index is not None:
                raise QuestionValidationError(
                    "Freeform question must not have options or correct_option_index."
                )

    @classmethod
    def new_id(cls) -> str:
        """Generate a new unique identifier for a question.  # F2"""
        return uuid.uuid4().hex

    def is_mcq(self) -> bool:
        """Return True if this question is a multiple-choice question."""
        return self.question_type is QuestionType.MCQ

    def is_freeform(self) -> bool:
        """Return True if this question expects a freeform answer."""
        return self.question_type is QuestionType.FREEFORM

    def record_result(self, is_correct: bool) -> None:
        """Delegate to stats for recording one answered attempt.  # F6, F7"""
        self.stats.record_result(is_correct)

    def to_dict(self) -> Dict[str, Any]:
        """Convert this question to a JSON-serialisable dict.  # F2"""
        return {
            "id": self.id,
            "topic": self.topic,
            "text": self.text,
            "question_type": self.question_type.value,
            "source": self.source.value,
            "active": self.active,
            "options": list(self.options),
            "correct_option_index": self.correct_option_index,
            "reference_answer": self.reference_answer,
            "stats": {
                "times_shown": self.stats.times_shown,
                "times_correct": self.stats.times_correct,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Question":
        """Create a Question from a dict (reverse of to_dict).  # F2, T2"""
        stats_data = data.get("stats", {})
        stats = QuestionStats(
            times_shown=int(stats_data.get("times_shown", 0)),
            times_correct=int(stats_data.get("times_correct", 0)),
        )

        return cls(
            id=str(data["id"]),
            topic=str(data["topic"]),
            text=str(data["text"]),
            question_type=QuestionType(data["question_type"]),
            source=QuestionSource(data["source"]),
            active=bool(data.get("active", True)),
            options=list(data.get("options", [])),
            correct_option_index=data.get("correct_option_index"),
            reference_answer=data.get("reference_answer"),
            stats=stats,
        )

    def __str__(self) -> str:  # pragma: no cover
        status = "active" if self.active else "inactive"
        return f"[{self.id}] ({self.topic}, {status}) {self.text}"
