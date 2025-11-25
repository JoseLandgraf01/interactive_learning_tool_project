from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence
import random

from learning_tool.models import Question
from learning_tool.repository import QuestionRepository


@dataclass
class QuizManager:
    """Coordinate quiz logic: selection, activation, stats.  # F5, F6, F7, NF1, NF3, NF8"""

    repository: QuestionRepository
    questions: List[Question] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.questions = self.repository.load_all()

    def _save(self) -> None:
        self.repository.save_all(self.questions)

    @staticmethod
    def _compute_weight(question: Question) -> float:
        """Return selection weight based on accuracy.  # F6"""
        if question.stats.times_shown == 0:
            return 1.0
        weight = 1.0 - question.stats.accuracy
        return max(weight, 0.1)

    @staticmethod
    def _choose_weighted(questions: Sequence[Question]) -> Question:
        weights = [QuizManager._compute_weight(q) for q in questions]
        return random.choices(list(questions), weights=weights, k=1)[0]

    def get_all_questions(self) -> List[Question]:
        """Return all known questions."""
        return list(self.questions)

    def get_active_questions(self) -> List[Question]:
        """Return only active questions.  # F5"""
        return [q for q in self.questions if q.active]

    def find_question_by_id(self, question_id: str) -> Optional[Question]:
        """Find a question by its identifier."""
        for question in self.questions:
            if question.id == question_id:
                return question
        return None

    def add_question(self, question: Question) -> None:
        """Add a new question and persist it.  # F3, F5"""
        self.questions.append(question)
        self._save()

    def set_question_active(self, question_id: str, active: bool) -> bool:
        """Enable or disable a question by ID.  # F5"""
        question = self.find_question_by_id(question_id)
        if question is None:
            return False
        question.active = active
        self._save()
        return True

    def toggle_question_active(self, question_id: str) -> bool:
        """Toggle the active flag for a question by ID.  # F5"""
        question = self.find_question_by_id(question_id)
        if question is None:
            return False
        question.active = not question.active
        self._save()
        return True

    def record_result(self, question: Question, is_correct: bool) -> None:
        """Record an answer result and persist it.  # F6, F7"""
        question.record_result(is_correct)
        self._save()

    def select_for_practice(self) -> Question:
        """Return one active question based on weighted randomness.  # F6, NF8"""
        active = self.get_active_questions()
        if not active:
            raise ValueError("No active questions available.")
        return self._choose_weighted(active)

    def select_for_test(self, count: int) -> List[Question]:
        """Return a list of distinct active questions for a test.  # F7"""
        active = self.get_active_questions()
        if count <= 0:
            raise ValueError("Number of questions must be positive.")
        if count > len(active):
            raise ValueError("Not enough active questions for requested test size.")
        return random.sample(active, count)
