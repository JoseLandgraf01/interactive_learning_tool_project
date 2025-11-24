from __future__ import annotations

import os
from typing import List, Dict, Any, Tuple

# from openai import OpenAI  # Uncomment and configure when using real OpenAI client.

from .config import CONFIG
from .logger_config import setup_logger

log = setup_logger(__name__)


class LLMClient:
    """Wrapper around an LLM API.

    Requirements:
        - FR-2: LLM question generation
        - FR-6, FR-7: Freeform evaluation
        - SEC-1, SEC-2, SEC-3, SEC-4
        - NFR-2: Robustness
        - NFR-8, NFR-9: Configurability & replaceability
    """

    def __init__(self) -> None:
        api_key = os.getenv(CONFIG.openai_api_key_env)
        if not api_key:
            log.warning(
                "No API key found in environment variable %s",
                CONFIG.openai_api_key_env,
            )
        # self.client = OpenAI(api_key=api_key)  # Example when using real client
        self.client = None
        self.model = CONFIG.llm_model

    def generate_questions(self, topic: str) -> List[Dict[str, Any]]:
        """Ask the LLM to generate questions for the given topic.

        Returns a list of dictionaries that can be turned into Question objects.

        In this skeleton we just log and return an empty list.
        """
        log.info("Would call LLM to generate questions for topic: %s", topic)
        # TODO: Implement real LLM call and JSON parsing.
        return []

    def evaluate_freeform(
        self, question_text: str, reference_answer: str, user_answer: str
    ) -> Tuple[bool, str]:
        """Evaluate a freeform answer using the LLM.

        Returns:
            (is_correct, explanation)
        """
        log.info("Would call LLM to evaluate freeform answer.")
        # TODO: Implement real LLM call for evaluation.
        # For now we just compare strings in a naive way.
        is_correct = user_answer.strip().lower() == reference_answer.strip().lower()
        explanation = "Naive evaluation (string equality) used as placeholder."
        return is_correct, explanation
