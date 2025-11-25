from __future__ import annotations

from datetime import datetime
from typing import List

from learning_tool.config import AppConfig, load_config
from learning_tool.exceptions import LearningToolError, LLMError
from learning_tool.llm_client import LLMClient, GeneratedQuestionSpec
from learning_tool.models import Question, QuestionSource, QuestionType
from learning_tool.quiz_manager import QuizManager
from learning_tool.repository import QuestionRepository


def main() -> None:
    """Entry point for the learning tool CLI.  # F1, NF4, NF5, NF6"""
    config = load_config()
    repo = QuestionRepository(path=config.questions_path)
    manager = QuizManager(repository=repo)
    llm_client = LLMClient()

    print("Welcome to the Learning Tool!")
    print(f"Environment: {config.env}")
    if not llm_client.is_available:
        # NF8: offline/testable behaviour.
        print("Note: No LLM configured, using simple built-in evaluation and generation.")

    while True:
        print_main_menu()
        choice = input("Select an option: ").strip()

        try:
            if choice == "1":
                handle_generate_questions(manager, llm_client)
            elif choice == "2":
                handle_practice_mode(manager, llm_client)
            elif choice == "3":
                handle_test_mode(manager, llm_client, config)
            elif choice == "4":
                handle_view_statistics(manager)
            elif choice == "5":
                handle_manage_questions(manager)
            elif choice == "0":
                print("Goodbye!")
                break
            else:
                print("Please choose a valid option (0-5).")
        except LearningToolError as exc:
            print(f"Error: {exc}")


def print_main_menu() -> None:
    """Display the main menu options.  # F1, NF4"""
    print()
    print("Main menu")
    print("---------")
    print("1. Generate questions (LLM or fallback)  [F3]")
    print("2. Practice mode                         [F6]")
    print("3. Test mode                             [F7]")
    print("4. View question statistics              [F4]")
    print("5. Manage questions (enable/disable)     [F5]")
    print("0. Exit")
    print()


# --- Generate Questions (F3) -------------------------------------------


def handle_generate_questions(manager: QuizManager, llm_client: LLMClient) -> None:
    """Generate new questions for a topic and let the user curate them.  # F3"""
    topic = input("Enter a topic for new questions (or leave blank to cancel): ").strip()
    if not topic:
        print("Cancelled.")
        return

    num_str = input("How many questions should I generate? [3]: ").strip()
    num_questions = 3
    if num_str:
        try:
            num_questions = int(num_str)
            if num_questions <= 0:
                raise ValueError
        except ValueError:
            print("Invalid number, using 3 questions.")
            num_questions = 3

    try:
        specs = llm_client.generate_questions(topic, num_questions)
    except (ValueError, LLMError) as exc:
        print(f"Could not generate questions: {exc}")
        return

    if not specs:
        print("No questions were generated.")
        return

    for index, spec in enumerate(specs, start=1):
        print()
        print(f"Question {index}/{len(specs)}")
        preview_generated_question(spec)

        while True:
            action = input("[a]ccept, [s]kip, [e]dit, [q]uit: ").strip().lower()
            if action not in {"a", "s", "e", "q"}:
                print("Please choose 'a', 's', 'e', or 'q'.")
                continue

            if action == "s":
                break
            if action == "q":
                return
            if action == "e":
                spec = edit_generated_question(spec)
                preview_generated_question(spec)
                continue

            if action == "a":
                question = build_question_from_spec(topic, spec)
                manager.add_question(question)
                print(f"Saved question with id: {question.id}")
                break


def preview_generated_question(spec: GeneratedQuestionSpec) -> None:
    """Print a human-friendly representation of a generated question spec."""
    print(f"Type: {spec.question_type.value}")
    print("Text:")
    print(f"  {spec.text}")
    if spec.question_type is QuestionType.MCQ and spec.options:
        print("Options:")
        for idx, option in enumerate(spec.options, start=1):
            marker = "*" if spec.correct_option_index == idx - 1 else " "
            print(f"  {idx}. {option} {marker}")


def edit_generated_question(spec: GeneratedQuestionSpec) -> GeneratedQuestionSpec:
    """Allow the user to edit basic fields of a generated question spec.  # F3, NF4"""
    print("Leave a field blank to keep the current value.")

    new_text = input("New question text: ").strip()
    if new_text:
        spec.text = new_text

    if spec.question_type is QuestionType.FREEFORM:
        current_ref = spec.reference_answer or ""
        print(f"Current reference answer: {current_ref!r}")
        new_ref = input("New reference answer: ").strip()
        if new_ref:
            spec.reference_answer = new_ref

    elif spec.question_type is QuestionType.MCQ and spec.options:
        print("Current options:")
        for idx, option in enumerate(spec.options, start=1):
            marker = "*" if spec.correct_option_index == idx - 1 else " "
            print(f"  {idx}. {option} {marker}")
        print("Editing options is not implemented in this simple CLI.")
        print("You can change them later by editing the JSON file directly.")

    return spec


def build_question_from_spec(topic: str, spec: GeneratedQuestionSpec) -> Question:
    """Create a persistent Question object from a generated spec.  # F3, F2"""
    if spec.question_type is QuestionType.MCQ:
        if not spec.options or spec.correct_option_index is None:
            raise LearningToolError("MCQ spec is missing options or correct index.")
        return Question(
            id=Question.new_id(),
            topic=topic,
            text=spec.text,
            question_type=QuestionType.MCQ,
            source=QuestionSource.LLM,
            options=list(spec.options),
            correct_option_index=spec.correct_option_index,
        )

    if spec.reference_answer is None:
        raise LearningToolError("Freeform spec must include a reference answer.")

    return Question(
        id=Question.new_id(),
            topic=topic,
            text=spec.text,
            question_type=QuestionType.FREEFORM,
            source=QuestionSource.LLM,
            reference_answer=spec.reference_answer,
        )


# --- Practice mode (F6) ------------------------------------------------


def handle_practice_mode(manager: QuizManager, llm_client: LLMClient) -> None:
    """Run an open-ended practice session until the user quits.  # F6"""
    if not manager.get_active_questions():
        print("There are no active questions to practice.")
        return

    print("Entering practice mode. Press Enter to continue, or 'q' to quit.")
    while True:
        proceed = input("[Enter/q]: ").strip().lower()
        if proceed == "q":
            break

        try:
            question = manager.select_for_practice()
        except ValueError as exc:
            print(exc)
            break

        is_correct = ask_question(question, llm_client)
        manager.record_result(question, is_correct)


# --- Test mode (F7) ----------------------------------------------------


def handle_test_mode(manager: QuizManager, llm_client: LLMClient, config: AppConfig) -> None:
    """Run a fixed-size test and record the score.  # F7, NF5, NF6"""
    active_questions = manager.get_active_questions()
    total_available = len(active_questions)
    if total_available == 0:
        print("There are no active questions available for testing.")
        return

    print(f"There are {total_available} active questions.")
    num_str = input("How many questions do you want in the test? ").strip()
    try:
        count = int(num_str)
    except ValueError:
        print("Invalid number; cancelling test.")
        return

    try:
        selected = manager.select_for_test(count)
    except ValueError as exc:
        print(exc)
        return

    correct = 0
    for question in selected:
        if ask_question(question, llm_client):
            correct += 1
            manager.record_result(question, True)
        else:
            manager.record_result(question, False)

    print()
    print(
        f"Your score: {correct} / {len(selected)} "
        f"({100 * correct / len(selected):.0f}%)"
    )

    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp} - score: {correct}/{len(selected)}\n"

    results_path = config.results_path
    try:
        contents = results_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        contents = ""
    results_path.write_text(contents + line, encoding="utf-8")


# --- Shared question-asking logic (F6, F7) -----------------------------


def ask_question(question: Question, llm_client: LLMClient) -> bool:
    """Display a question, collect an answer, and return correctness.  # F6, F7"""
    print()
    print(f"Topic: {question.topic}")
    print(question.text)

    if question.is_mcq():
        return ask_mcq_question(question)
    return ask_freeform_question(question, llm_client)


def ask_mcq_question(question: Question) -> bool:
    """Ask a multiple-choice question and check correctness locally.  # F6, F7"""
    assert question.options is not None
    assert question.correct_option_index is not None

    for idx, option in enumerate(question.options, start=1):
        print(f"  {idx}. {option}")

    while True:
        answer = input("Your answer (number): ").strip()
        try:
            index = int(answer) - 1
        except ValueError:
            print("Please enter a valid number.")
            continue

        if not 0 <= index < len(question.options):
            print("Number out of range, try again.")
            continue

        is_correct = index == question.correct_option_index
        if is_correct:
            print("Correct!")
        else:
            correct_option = question.options[question.correct_option_index]
            print(f"Incorrect. Correct answer: {correct_option}")
        return is_correct


def ask_freeform_question(question: Question, llm_client: LLMClient) -> bool:
    """Ask a freeform question and use LLM (or heuristic) to evaluate it.  # F6"""
    assert question.reference_answer is not None

    user_answer = input("Your answer: ").strip()
    if not user_answer:
        print("You entered an empty answer; counting as incorrect.")
        return False

    try:
        is_correct, explanation = llm_client.evaluate_freeform(
            question_text=question.text,
            reference_answer=question.reference_answer,
            user_answer=user_answer,
        )
    except (ValueError, LLMError) as exc:
        print(f"Could not evaluate answer automatically: {exc}")
        print("Assuming the answer is incorrect.")
        return False

    print("Evaluation:")
    print(explanation)
    print("Result:", "Correct!" if is_correct else "Incorrect.")
    return is_correct


# --- Statistics & management (F4, F5) ---------------------------------


def handle_view_statistics(manager: QuizManager) -> None:
    """Display all questions with basic statistics.  # F4"""
    questions = manager.get_all_questions()
    if not questions:
        print("No questions stored yet.")
        return

    print()
    print(f"{'ID':8} {'Act':3} {'Type':8} {'Topic':20} {'Shown':5} {'Correct':7} {'Acc':5}")
    print("-" * 70)
    for q in questions:
        acc = f"{100 * q.stats.accuracy:.0f}%" if q.stats.times_shown else "--"
        print(
            f"{q.id[:8]:8} "
            f"{'Y' if q.active else 'N':3} "
            f"{q.question_type.value:8} "
            f"{q.topic[:20]:20} "
            f"{q.stats.times_shown:5d} "
            f"{q.stats.times_correct:7d} "
            f"{acc:5}"
        )


def handle_manage_questions(manager: QuizManager) -> None:
    """Allow the user to toggle question active status by ID prefix.  # F5"""
    questions = manager.get_all_questions()
    if not questions:
        print("No questions stored yet.")
        return

    print()
    print("Existing questions:")
    for q in questions:
        print(f"  {q.id[:8]} - {'[active]' if q.active else '[inactive]'} - {q.topic}")

    while True:
        choice = input(
            "Enter question ID prefix to toggle (or blank to return): "
        ).strip()
        if not choice:
            break

        matched: List[Question] = [q for q in questions if q.id.startswith(choice)]
        if not matched:
            print("No question found with that prefix.")
            continue
        if len(matched) > 1:
            print("Ambiguous prefix; please enter more characters.")
            continue

        question = matched[0]
        manager.toggle_question_active(question.id)
        status = "active" if question.active else "inactive"
        print(f"Question {question.id[:8]} is now {status}.")
