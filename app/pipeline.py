
import time
from datetime import datetime, timezone

from app.query_analyzer import analyze_query
from app.retriever import PaperRetriever
from app.decision_engine import DecisionEngine
from app.generator import AnswerGenerator
from app.validator import CitationValidator
from app.csv_logger import CSVLogger


class RelayPipeline:

    RETRIEVAL_SETTING = (
        "BM25_chunk500_top3_retry8_threshold1.0"
    )

    def __init__(self):

        print("Initializing The Relay...")

        self.retriever = PaperRetriever()

        self.decision_engine = DecisionEngine(
            self.retriever,
            minimum_score=1.0
        )

        self.generator = AnswerGenerator()
        self.validator = CitationValidator()
        self.csv_logger = CSVLogger()

        print("The Relay is ready!")

    def process(
        self,
        question,
        scenario="functional_baseline"
    ):

        # Measure the complete pipeline request.
        start_clock = time.perf_counter()

        start_time = datetime.now(
            timezone.utc
        ).isoformat()

        try:

            result = self._process(question)

        except Exception as error:

            result = {
                "status": "error",
                "question": question,
                "answer": (
                    "The application encountered an "
                    "unexpected error."
                ),
                "citations": [],
                "error": str(error)
            }

        total_ms = round(
            (time.perf_counter() - start_clock) * 1000,
            2
        )

        metrics = result.pop("_metrics", {})

        # Convert pipeline outcomes into the assignment's
        # permitted CSV status values.
        pipeline_status = result.get("status", "error")

        if pipeline_status in {
            "ok",
            "refused_correctly"
        }:
            csv_status = "ok"

        elif pipeline_status in {
            "rate_limited",
            "timeout"
        }:
            csv_status = pipeline_status

        else:
            csv_status = "error"

        # Record correct refusals separately from API failures.
        if pipeline_status == "refused_correctly":
            answer_grade = "refused_correctly"
        else:
            answer_grade = ""

        request_id = self.csv_logger.log_request(
            scenario=scenario,
            source="real",
            start_time=start_time,
            first_token_ms=metrics.get("first_token_ms"),
            total_ms=total_ms,
            status=csv_status,
            retries=metrics.get("retries", 0),
            tokens_in=metrics.get("tokens_in"),
            tokens_out=metrics.get("tokens_out"),
            retrieval_setting=self.RETRIEVAL_SETTING,
            answer_grade=answer_grade
        )

        result["request_id"] = request_id
        result["total_ms"] = total_ms

        print(
            f"\nCSV log saved. Request ID: {request_id}"
        )

        return result

    def _process(self, question):

        print("\nProcessing user question...")

        # STEP 1: Analyze query.
        query_data = analyze_query(question)

        print(
            "Question type:",
            query_data["question_type"]
        )

        # STEP 2 and 3: Retrieve evidence and make a decision.
        decision = self.decision_engine.retrieve_evidence(
            query_data["search_query"]
        )

        evidence = decision["evidence"]

        print(
            "Retrieval attempts:",
            decision["retrieval_attempts"]
        )

        print(
            "Retrieved passages:",
            len(evidence)
        )

        # STEP 4: Refuse if retrieval finds insufficient evidence.
        if not decision["sufficient"]:

            return {
                "status": "refused_correctly",
                "question": question,
                "answer": (
                    "I cannot provide a reliable answer "
                    "because the available research papers "
                    "do not provide sufficient evidence "
                    "for this question."
                ),
                "citations": [],
                "retrieval_attempts": (
                    decision["retrieval_attempts"]
                ),
                "_metrics": {}
            }

        # STEP 5: Generate response.
        generated = self.generator.generate(
            question,
            evidence
        )

        generated_status = generated.get(
            "status",
            "error"
        )

        # Preserve the model's evidence-based refusal.
        if generated_status == "refused_correctly":

            return {
                "status": "refused_correctly",
                "question": question,
                "answer": generated["answer"],
                "citations": [],
                "retrieval_attempts": (
                    decision["retrieval_attempts"]
                ),
                "_metrics": {
                    "first_token_ms": generated.get(
                        "first_token_ms"
                    ),
                    "tokens_in": generated.get("tokens_in"),
                    "tokens_out": generated.get("tokens_out"),
                    "retries": generated.get("retries", 0)
                }
            }

        # Handle API errors and response validation failures.
        if generated_status != "ok":

            return {
            "status": generated_status,
            "question": question,
            "answer": (
                "The AI service could not complete "
                "your request. Please try again later."
            ),
            "citations": [],
            "error": generated.get("error"),
            "retry_after_seconds": generated.get(
                "retry_after_seconds"
            ),
            "rate_limit_headers": generated.get(
                "rate_limit_headers", {}
            ),
            "retrieval_attempts": decision["retrieval_attempts"],
            "_metrics": {
                "first_token_ms": generated.get("first_token_ms"),
                "tokens_in": generated.get("tokens_in"),
                "tokens_out": generated.get("tokens_out"),
                "retries": generated.get("retries", 0)
            }
        }
        # STEP 6: Validate citation references and metadata.
        validation = self.validator.validate(
            generated,
            evidence
        )

        if not validation["valid"]:

            return {
                "status": "validation_failed",
                "question": question,
                "answer": (
                    "The generated response could not "
                    "pass citation validation."
                ),
                "citations": [],
                "validation_reason": validation["reason"],
                "retrieval_attempts": (
                    decision["retrieval_attempts"]
                ),
                "_metrics": {
                    "first_token_ms": generated.get(
                        "first_token_ms"
                    ),
                    "tokens_in": generated.get("tokens_in"),
                    "tokens_out": generated.get("tokens_out"),
                    "retries": generated.get("retries", 0)
                }
            }

        # STEP 7: Return the validated answer.
        return {
            "status": "ok",
            "question": question,
            "answer": generated["answer"],
            "citations": generated["citations"],
            "retrieval_attempts": (
                decision["retrieval_attempts"]
            ),
            "validation": validation,
            "_metrics": {
                "first_token_ms": generated.get(
                    "first_token_ms"
                ),
                "tokens_in": generated.get("tokens_in"),
                "tokens_out": generated.get("tokens_out"),
                "retries": generated.get("retries", 0)
            }
        }


if __name__ == "__main__":

    relay = RelayPipeline()

    print("\n" + "=" * 55)
    print("THE RELAY - AI RESEARCH ASSISTANT")
    print("=" * 55)

    while True:

        question = input(
            "\nAsk a research question "
            "(or type exit): "
        )

        if question.strip().lower() == "exit":
            print("Closing The Relay...")
            break

        result = relay.process(question)

        print("\n" + "=" * 55)
        print("FINAL RESPONSE")
        print("=" * 55)

        print("Status:", result["status"])
        print("\nAnswer:")
        print(result["answer"])

        print("\nCitations:")

        for citation in result.get("citations", []):

            print(
                f"- {citation['title']} "
                f"(arXiv:{citation['paper_id']}, "
                f"v{citation['version']}, "
                f"PDF page {citation['pdf_page']})"
            )

        if "validation" in result:
            print(
                "\nCitation validation:",
                result["validation"]["reason"]
            )

        if "validation_reason" in result:
            print(
                "\nValidation error:",
                result["validation_reason"]
            )

        if "error" in result and result["error"]:
            print("\nError:", result["error"])

        print("\nTotal pipeline time:", result["total_ms"], "ms")
