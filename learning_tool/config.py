from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppConfig:
    """Configuration for paths and environment.  # NF5, NF6"""

    env: str
    base_dir: Path
    questions_path: Path
    results_path: Path


def load_config() -> AppConfig:
    """Load configuration from environment variables.  # NF5, NF6"""

    env = os.getenv("LEARNING_TOOL_ENV", "dev").lower()
    if env not in {"dev", "prod"}:
        env = "dev"

    base_dir = Path(os.getenv("LEARNING_TOOL_BASE_DIR", ".")).expanduser().resolve()

    return AppConfig(
        env=env,
        base_dir=base_dir,
        questions_path=base_dir / "questions.json",
        results_path=base_dir / "results.txt",
    )
