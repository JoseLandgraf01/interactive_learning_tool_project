from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import os

# Base directories (portable across OSes)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"


@dataclass(frozen=True)
class AppConfig:
    """Central application configuration.

    Requirements:
        - FR-11: Central configuration
        - NFR-7: Portability
        - NFR-8: Configurability
    """

    questions_file: Path = DATA_DIR / "questions.json"
    results_file: Path = DATA_DIR / "results.txt"
    log_dir: Path = LOG_DIR
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    openai_api_key_env: str = "OPENAI_API_KEY"


CONFIG = AppConfig()
