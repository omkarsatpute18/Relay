
import time
from datetime import datetime, timezone

from app.query_analyzer import analyze_query
from app.retriever import PaperRetriever
from app.decision_engine import DecisionEngine
from app.generator import AnswerGenerator
from app.validator import CitationValidator
from app.csv_logger import CSVLogger


class RelayPipeline:

    def __init__(self):

        self.retriever = PaperRetriever()

        self.decision_engine = DecisionEngine(
            retriever=self.retriever,
            minimum_score=1.0
        )

        self.generator = AnswerGenerator()
        self.validator = CitationValidator()
        self.logger = CSVLogger()

    def process(
        self,
        question,
        scenario="real_baseline",
        retrieval_setting="adaptive_top3_top8"
    ):

        start_time = time.perf_counter()
        start_timestamp = datetime.now(timezone.utc).isoformat()

        try:
            result = self._process(
                question,
                retrieval_setting
            )

        except Exception as error:
            result = {
                "status": "error",
                "answer": "",
                "citations": [],
                "error": str(error),
                "_metrics": {},
            }

        total_ms = (time.perf_counter() - start_time) * 1000

        metrics = result.pop("_metrics", {})
        pipeline_status = result.get("status", "error")

        if pipeline_status in {"ok", "refused_correctly"}:
            csv_status = "ok"
        elif pipeline_status == "rate_limited":
            csv_status = "rate_limited"
        elif pipeline_status == "timeout":
            csv_status = "timeout"
        else:
            csv_status = "error"

        answer_grade = ""

        if pipeline_status == "refused_correctly":
            answer_grade = "refused_correctly"

        request_id = self.logger.log_request(
            scenario=scenario,
            source="real",
            start_time=start_timestamp,
            first_token_ms=metrics.get("first_token_ms"),
            total_ms=total_ms,
            status=csv_status,
            retries=metrics.get("retries", 0),
            tokens_in=metrics.get("tokens_in"),
            tokens_out=metrics.get("tokens_out"),
            retrieval_setting=retrieval_setting,
            answer_grade=answer_grade,
        )

        result["request_id"] = request_id
        result["total_ms"] = total_ms
        result["retries"] = metrics.get("retries", 0)
        result["tokens_in"] = metrics.get("tokens_in")
        result["tokens_out"] = metrics.get("tokens_out")
        result["first_token_ms"] = metrics.get("first_token_ms")
        result["retrieval_setting"] = retrieval_setting

        return result

    def _process(self, question, retrieval_setting):

        # STEP 1: Analyze the question.
        analyzed_query = analyze_query(question)
        search_query = analyzed_query["search_query"]

        # STEP 2: Retrieve evidence using the selected setting.
        decision = self.decision_engine.retrieve_evidence(
            search_query,
            retrieval_setting=retrieval_setting
        )

        retrieved_chunks = decision["evidence"]

        metrics = {
            "retrieval_setting": retrieval_setting,
            "retrieval_attempts": decision["retrieval_attempts"],
        }

        # STEP 3: Refuse if sufficient evidence is unavailable.
        if not decision["sufficient"]:

            return {
                "status": "refused_correctly",
                "answer": (
                    "I cannot answer this question using the "
                    "available research papers."
                ),
                "citations": [],
                "_metrics": metrics,
            }

        # STEP 4: Generate an answer using Groq.
        generated = self.generator.generate(
            question=question,
            evidence=retrieved_chunks,
        )

        generated_status = generated.get("status", "error")

        metrics.update({
            "first_token_ms": generated.get("first_token_ms"),
            "tokens_in": generated.get("tokens_in"),
            "tokens_out": generated.get("tokens_out"),
            "retries": generated.get("retries", 0),
        })

        # Handle a correct model refusal.
        if generated_status == "refused_correctly":

            return {
                "status": "refused_correctly",
                "answer": generated.get("answer", ""),
                "citations": [],
                "_metrics": metrics,
            }

        # Handle API and generation errors.
        if generated_status != "ok":

            return {
                "status": generated_status,
                "answer": "",
                "citations": [],
                "error": generated.get("error"),
                "retry_after_seconds": generated.get(
                    "retry_after_seconds"
                ),
                "rate_limit_headers": generated.get(
                    "rate_limit_headers", {}
                ),
                "_metrics": metrics,
            }

        # STEP 5: Validate citations.
        citations = generated.get("citations", [])

        validation = self.validator.validate(
            generated,
            retrieved_chunks,
        )

        if not validation.get("valid", False):

            return {
                "status": "validation_failed",
                "answer": generated.get("answer", ""),
                "citations": citations,
                "error": validation.get(
                    "reason",
                    "Citation validation failed."
                ),
                "_metrics": metrics,
            }

        # STEP 6: Return the final answer.
        return {
            "status": "ok",
            "answer": generated.get("answer", ""),
            "citations": citations,
            "_metrics": metrics,
        }
