import csv
import os
import tempfile
from pathlib import Path

from app.pipeline import RelayPipeline


ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_FILE = ROOT_DIR / "results" / "results.csv"

QUESTIONS = [
    "What is the main idea behind the Transformer architecture?",
    "How does multi-head attention work?",
    "What is the role of positional encoding in Transformers?",
    "How does Moshi support real-time dialogue?",
    "What is the purpose of Inner Monologue in Moshi?",
    "How does dynamic chunking work in hierarchical sequence modeling?",
    "What problem does dynamic chunking try to address?",
    "What is the capital of Japan?",
    "Who won the FIFA World Cup in 2022?",
    "What is the difference between encoder self-attention and decoder masked self-attention in the Transformer?",
    "Why does the Transformer scale dot-product attention by the square root of the key dimension?",
    "How do recurrent, convolutional, and self-attention layers compare in sequential operations and maximum path length?",
    "What does Inner Monologue add to Moshi, and how does it support streaming speech recognition and speech generation?",
    "How does the routing module identify chunk boundaries, and what does the downsampler do?",
    "What is the current USD to INR exchange rate?",
]

RETRIEVAL_SETTINGS = {
    "1": "bm25_top3",
    "2": "bm25_top5",
    "3": "bm25_top8",
    "4": "adaptive_top3_top8",
}

GRADES = {
    "1": "correct",
    "2": "wrong",
    "3": "refused_correctly",
    "4": "refused_wrongly",
    "5": "",
}


def update_answer_grade(request_id, grade):
    """Update the just-created CSV row using its unique request_id."""
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(f"Results file not found: {RESULTS_FILE}")

    with RESULTS_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames or "request_id" not in fieldnames or "answer_grade" not in fieldnames:
        raise ValueError("results.csv does not contain the required request_id and answer_grade columns.")

    found = False
    for row in rows:
        if row.get("request_id") == request_id:
            row["answer_grade"] = grade
            found = True
            break

    if not found:
        raise ValueError(f"Could not find request_id {request_id} in results.csv")

    fd, temporary_path = tempfile.mkstemp(
        prefix="results_", suffix=".csv", dir=str(RESULTS_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_path, RESULTS_FILE)
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


def main():
    print("\n===== RELAY 15-QUESTION EVALUATION =====")
    for index, question in enumerate(QUESTIONS, start=1):
        print(f"{index:2}. {question}")

    try:
        question_number = int(input("\nEnter question number to run (1-15): ").strip())
    except ValueError:
        print("Invalid input. Enter a number from 1 to 15.")
        return

    if not 1 <= question_number <= len(QUESTIONS):
        print("Please enter a number between 1 and 15.")
        return

    print("\nChoose a retrieval setting:")
    print("1. BM25 top 3")
    print("2. BM25 top 5")
    print("3. BM25 top 8")
    print("4. Adaptive top 3, then top 8")

    setting_choice = input("Enter setting (1-4): ").strip()
    if setting_choice not in RETRIEVAL_SETTINGS:
        print("Invalid retrieval setting. Choose 1, 2, 3, or 4.")
        return

    question = QUESTIONS[question_number - 1]
    retrieval_setting = RETRIEVAL_SETTINGS[setting_choice]

    print(f"\nRunning Question {question_number}...")
    print("Question:", question)
    print("Retrieval setting:", retrieval_setting)

    try:
        relay = RelayPipeline()
        result = relay.process(
            question,
            scenario="retrieval_quality_evaluation",
            retrieval_setting=retrieval_setting,
        )
    except Exception as error:
        print("Pipeline error:", error)
        return

    print("\n===== RESULT =====")
    print("Status:", result.get("status"))
    print("Answer:", result.get("answer", "No answer returned."))
    print("Citations:", result.get("citations", []))
    print("Total time (ms):", result.get("total_ms"))
    print("First token time (ms):", result.get("first_token_ms"))
    print("Retries:", result.get("retries"))
    print("Input tokens:", result.get("tokens_in"))
    print("Output tokens:", result.get("tokens_out"))

    if result.get("error"):
        print("Error:", result.get("error"))

    request_id = result.get("request_id")
    status = result.get("status")
    if not request_id:
        print("\nNo request ID was returned, so no answer grade was saved.")
        return

    if status not in {"ok", "refused_correctly"}:
        print("\nThis request did not produce a completed answer. Its answer grade was left blank.")
        print("The request and service status are still logged in results.csv.")
        return

    print("\n===== HUMAN ANSWER GRADING =====")
    print("Compare the answer with the cited paper passages, not just whether it sounds plausible.")
    print("1. Correct")
    print("2. Wrong / unsupported / materially inaccurate")
    print("3. Refused correctly (the papers do not contain the answer)")
    print("4. Refused incorrectly (the papers contain enough evidence to answer)")
    print("5. Skip grading for now")

    grade_choice = input("Enter grade (1-5): ").strip()
    if grade_choice not in GRADES:
        print("Invalid grade. The answer_grade field was left unchanged.")
        return

    grade = GRADES[grade_choice]
    if grade == "":
        print("Grade skipped. You can grade this answer later.")
        return

    try:
        update_answer_grade(request_id, grade)
        print(f"Saved answer grade: {grade}")
        print("The result and its human grade are saved in results/results.csv.")
    except Exception as error:
        print("The answer was generated, but its grade could not be saved:", error)
        print("Request ID:", request_id)


if __name__ == "__main__":
    main()
