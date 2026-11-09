
from app.query_analyzer import analyze_query
from app.retriever import PaperRetriever
from app.decision_engine import DecisionEngine
from app.generator import AnswerGenerator
from app.validator import CitationValidator


class RelayPipeline:

    def __init__(self):

        print("Initializing The Relay...")

        # Initialize retrieval tool
        self.retriever = PaperRetriever()

        # Initialize decision engine
        self.decision_engine = DecisionEngine(
            self.retriever,
            minimum_score=1.0
        )

        # Initialize answer generator
        self.generator = AnswerGenerator()

        # Initialize citation validator
        self.validator = CitationValidator()

        print("The Relay is ready!")

    def process(self, question):

        print("\nProcessing user question...")

        # STEP 1: Analyze query
        query_data = analyze_query(question)

        print(
            "Question type:",
            query_data["question_type"]
        )

        # STEP 2 and 3: Retrieve and make decision
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

        # STEP 4: Branch if evidence is insufficient
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
                )
            }

        # STEP 5: Generate response
        generated = self.generator.generate(
            question,
            evidence
        )

        # Handle a correct evidence-based refusal
        if generated.get("status") == "refused_correctly":

            return {
                "status": "refused_correctly",
                "question": question,
                "answer": generated["answer"],
                "citations": [],
                "retrieval_attempts": decision["retrieval_attempts"]
            }


        # Handle API errors and validation failures
        if generated.get("status") != "ok":

            return {
                "status": generated.get("status", "error"),
                "question": question,
                "answer": (
                    "The AI service could not complete "
                    "your request. Please try again later."
                ),
                "citations": [],
                "error": generated.get("error")
        }
        # STEP 6: Validate citations
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
                "validation_reason": validation["reason"]
            }

        # STEP 7: Return final response
        return {
            "status": "ok",
            "question": question,
            "answer": generated["answer"],
            "citations": generated["citations"],
            "retrieval_attempts": (
                decision["retrieval_attempts"]
            ),
            "validation": validation
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

        try:

            result = relay.process(question)

            print("\n" + "=" * 55)
            print("FINAL RESPONSE")
            print("=" * 55)

            print("Status:", result["status"])
            if "validation_reason" in result:
                print("Validation error:", result["validation_reason"])

            if "error" in result:
                print("Error:", result["error"])
            print("\nAnswer:")
            print(result["answer"])

            print("\nCitations:")

            for citation in result.get(
                "citations", []
            ):

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

        except Exception as error:

            print("\nPipeline error:", str(error))
if "validation_reason" in result:
    print(
        "\nValidation error:",
        result["validation_reason"]
    )

if "error" in result:
    print("\nError:", result["error"])