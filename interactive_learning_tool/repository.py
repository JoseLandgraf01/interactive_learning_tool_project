from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .config import CONFIG
from .models import Question, question_from_dict, question_to_dict
from .logger_config import setup_logger


log = setup_logger(__name__)


class QuestionRepository:
    """Manage loading and saving questions to JSON.

    Requirements:
        - FR-3: Data persistence
        - FR-5: Manage questions
        - NFR-2: Robustness
        - NFR-6: Data integrity
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or CONFIG.questions_file
        self._questions: List[Question] = []
        self._next_id: int = 1

    @property
    def questions(self) -> List[Question]:
        return list(self._questions)

    def load(self) -> None:
        if not self.path.exists():
            log.warning("Questions file does not exist yet: %s", self.path)
            self._questions = []
            self._next_id = 1
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            log.error("Failed to parse questions file: %s", exc)
            self._questions = []
            self._next_id = 1
            return

        self._questions = [question_from_dict(d) for d in raw]
        self._next_id = (max((q.id for q in self._questions), default=0) + 1)

    def save(self) -> None:
        data = [question_to_dict(q) for q in self._questions]
        self.path.parent.mkdir(exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, question: Question) -> None:
        question.id = self._next_id
        self._next_id += 1
        self._questions.append(question)

    def find_by_id(self, qid: int) -> Optional[Question]:
        for q in self._questions:
            if q.id == qid:
                return q
        return None

    def active_questions(self) -> List[Question]:
        return [q for q in self._questions if q.active]
