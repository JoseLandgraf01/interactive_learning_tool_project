from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import json
import logging

from .exceptions import PersistenceError
from .models import Question

logger = logging.getLogger(__name__)


@dataclass
class QuestionRepository:
    """JSON-based storage for questions and their statistics.  # F2, NF3, NF5"""

    path: Path

    def load_all(self) -> List[Question]:
        """Load all questions from the JSON file.  # F2, T2"""
        if not self.path.exists():
            return []

        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            logger.exception("Failed to read %s", self.path)
            raise PersistenceError(f"Failed to read {self.path}") from exc

        if not text.strip():
            return []

        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.exception("Invalid JSON in %s", self.path)
            raise PersistenceError(f"Invalid JSON in {self.path}") from exc

        if not isinstance(raw, list):
            raise PersistenceError("Root JSON value must be a list of questions.")

        questions: List[Question] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                question = Question.from_dict(item)
            except Exception:
                logger.warning("Skipping malformed question entry: %r", item)
                continue
            questions.append(question)
        return questions

    def save_all(self, questions: List[Question]) -> None:
        """Persist all questions to the JSON file.  # F2, T2"""
        payload = [q.to_dict() for q in questions]
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:  # pragma: no cover
            logger.exception("Failed to write %s", self.path)
            raise PersistenceError(f"Failed to write {self.path}") from exc
