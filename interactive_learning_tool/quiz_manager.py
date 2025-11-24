from __future__ import annotations

import random
from typing import List

from .models import Question, MCQQuestion, FreeformQuestion
from .repository import QuestionRepository
from .llm_client import LLMClient
from .logger_config import setup_logger


log = setup_logger(__name__)


class QuizManager:
    """Orchestrate practice and test modes.

    Requirements:
        - FR-4, FR-5, FR-6, FR-7
        - NFR-1, NFR-2, NFR-9
    """

    def __init__(self, repo: QuestionRepository, llm: LLMClient) -> None:
        self.repo = repo
        self.llm = llm

    def _weight_for_question(self, q: Question) -> float:
        """Compute a weight for adaptive practice.

        Simple heuristic:
            - If never shown: high weight.
            - Otherwise: 1 + (times_shown - times_correct)

        This satisfies FR-6 (adaptive) in a simple way.
        """
        if q.stats.shown == 0:
            return 5.0
        return 1.0 + (q.stats.shown - q.stats.correct)

    def choose_practice_question(self) -> Question:
        active = self.repo.active_questions()
        if not active:
            raise RuntimeError("No active questions available.")

        weights = [self._weight_for_question(q) for q in active]
        chosen = random.choices(active, weights=weights, k=1)[0]
        log.info("Selected question %s for practice", chosen.id)
        return chosen

    def choose_test_questions(self, count: int) -> List[Question]:
        active = self.repo.active_questions()
        if count > len(active):
            raise ValueError("Not enough active questions for requested test size.")
        return random.sample(active, count)
