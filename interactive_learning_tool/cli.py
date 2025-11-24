from __future__ import annotations

from .repository import QuestionRepository
from .llm_client import LLMClient
from .quiz_manager import QuizManager
from .logger_config import setup_logger


log = setup_logger(__name__)


def main() -> None:
    """Entry point for the CLI application.

    Requirements:
        - FR-1: Main menu
        - FR-10: CLI interaction quality
    """
    repo = QuestionRepository()
    repo.load()
    llm = LLMClient()
    manager = QuizManager(repo, llm)

    while True:
        print("\n=== Interactive Learning Tool ===")
        print("1) Generate questions (LLM)   [FR-2]")
        print("2) View statistics            [FR-4]")
        print("3) Practice mode              [FR-6]")
        print("4) Test mode                  [FR-7]")
        print("5) Manage questions           [FR-5]")
        print("0) Exit")
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            print("(Stub) Generate questions not implemented in skeleton.")
        elif choice == "2":
            print("(Stub) Statistics view not implemented in skeleton.")
        elif choice == "3":
            print("(Stub) Practice mode not fully implemented in skeleton.")
        elif choice == "4":
            print("(Stub) Test mode not fully implemented in skeleton.")
        elif choice == "5":
            print("(Stub) Manage questions not implemented in skeleton.")
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main()
