import csv
import json
import os
import tempfile
from pathlib import Path

from app.pipeline import RelayPipeline

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
RESULTS_FILE = RESULTS_DIR / "results.csv"
PROGRESS_FILE = RESULTS_DIR / "retrieval_comparison_progress.json"

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

SETTINGS = {
    "1": ("bm25_top3", "BM25 Top 3"),
    "2": ("bm25_top5", "BM25 Top 5"),
    "3": ("bm25_top8", "BM25 Top 8"),
    "4": ("adaptive_top3_top8", "Adaptive Top 3–8"),
}

GRADES = {
    "1": "correct",
    "2": "wrong",
    "3": "refused_correctly",
    "4": "refused_wrongly",
    "5": "",
}


def load_progress():
    if not PROGRESS_FILE.exists():
        return {"version": 1, "completed": {}}
    with PROGRESS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("completed"), dict):
        raise ValueError("Progress file has an unexpected format.")
    return data


def save_progress(data):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix="retrieval_progress_", suffix=".json", dir=RESULTS_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, PROGRESS_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def update_answer_grade(request_id, grade):
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(f"Results file not found: {RESULTS_FILE}")
    with RESULTS_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    if not fields or not {"request_id", "answer_grade"}.issubset(fields):
        raise ValueError("results.csv is missing required columns.")
    found = False
    for row in rows:
        if row.get("request_id") == request_id:
            row["answer_grade"] = grade
            found = True
            break
    if not found:
        raise ValueError(f"Request ID {request_id} was not found.")
    fd, temp_path = tempfile.mkstemp(prefix="results_", suffix=".csv", dir=RESULTS_DIR)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp_path, RESULTS_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def display_result(number, question, label, result):
    print("\\n" + "=" * 70)
    print(f"Question {number}/15 — {label}")
    print("Question:", question)
    print("Status:", result.get("status"))
    print("\\nAnswer:\\n", result.get("answer") or "[No answer returned]")
    print("\\nCitations:")
    citations = result.get("citations") or []
    if not citations:
        print("No citations returned.")
    for c in citations:
        print(
            f"- {c.get('title')} | arXiv:{c.get('paper_id')} v{c.get('version')} "
            f"| PDF page {c.get('pdf_page')} | chunk {c.get('chunk_id')}"
        )
    print("\\nMeasurements:")
    for key, label_text in [
        ("total_ms", "Total pipeline time (ms)"),
        ("first_token_ms", "First-token time (ms)"),
        ("tokens_in", "Input tokens"),
        ("tokens_out", "Output tokens"),
        ("retries", "Retries"),
        ("request_id", "Request ID"),
    ]:
        print(f"{label_text}: {result.get(key)}")
    if result.get("error"):
        print("Error:", result["error"])


def get_grade():
    print("\\nGrade the answer against the research papers:")
    print("1. Correct and adequately supported")
    print("2. Wrong, unsupported, or materially inaccurate")
    print("3. Refused correctly because the papers do not contain the answer")
    print("4. Refused incorrectly even though the papers contain enough evidence")
    print("5. Skip grading for now")
    while True:
        choice = input("Enter grade (1–5): ").strip()
        if choice in GRADES:
            return GRADES[choice]
        print("Invalid choice. Enter 1, 2, 3, 4, or 5.")


def main():
    print("\\n===== RELAY RETRIEVAL COMPARISON =====")
    print("One retrieval setting is run per session. Progress is saved after each question.")
    print("\\nChoose a retrieval setting:")
    for key, (_, label) in SETTINGS.items():
        print(f"{key}. {label}")
    choice = input("Enter setting (1–4): ").strip()
    if choice not in SETTINGS:
        print("Invalid setting.")
        return

    setting, label = SETTINGS[choice]
    progress = load_progress()
    completed = progress["completed"].setdefault(setting, {})
    pending = [(i, q) for i, q in enumerate(QUESTIONS, 1) if str(i) not in completed]

    print(f"\\nSelected: {label}")
    print(f"Already completed or skipped: {15 - len(pending)}/15")
    print(f"Remaining: {len(pending)}")
    if not pending:
        print("This setting is already complete.")
        return
    if input(f"Run the {len(pending)} remaining questions? (y/n): ").strip().lower() != "y":
        print("No requests sent.")
        return

    try:
        pipeline = RelayPipeline()
    except Exception as error:
        print("Could not initialize pipeline:", error)
        return

    for number, question in pending:
        print(f"\\nRunning question {number}/15 with {label}...")
        try:
            result = pipeline.process(
                question,
                scenario=f"retrieval_comparison_{setting}",
                retrieval_setting=setting,
            )
        except KeyboardInterrupt:
            print("\\nStopped. Previously saved progress is preserved.")
            return
        except Exception as error:
            print("Experiment error:", error)
            print("This question remains pending.")
            continue

        display_result(number, question, label, result)
        request_id = result.get("request_id")
        status = result.get("status")

        if not request_id:
            print("No request ID. This question remains pending.")
            continue
        if status not in {"ok", "refused_correctly"}:
            print("No completed answer. This question remains pending for a later retry.")
            continue

        grade = get_grade()
        try:
            if grade:
                update_answer_grade(request_id, grade)
                progress_status = "graded"
                print("Saved grade:", grade)
            else:
                progress_status = "skipped"
                print("Skipped. The request remains in results.csv for later manual grading.")

            completed[str(number)] = {
                "request_id": request_id,
                "grade": grade,
                "progress_status": progress_status,
            }
            save_progress(progress)
        except Exception as error:
            print("Could not save grade/progress:", error)
            print("Request ID:", request_id)
            print("The request itself is still logged in results.csv.")
            print("Check that CSV row before rerunning this question.")

    print("\\n===== SETTING SUMMARY =====")
    print(f"{setting}: {len(completed)}/15 completed or skipped")
    print("Progress:", PROGRESS_FILE)
    print("Results:", RESULTS_FILE)
    if len(completed) == len(QUESTIONS):
        print("This setting is complete. You can run the next setting.")
    else:
        print("Some questions remain. Run this script again with the same setting to resume.")


if __name__ == "__main__":
    main()
