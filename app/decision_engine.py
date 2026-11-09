
class DecisionEngine:

    def __init__(
        self,
        retriever,
        minimum_score=1.0
    ):

        self.retriever = retriever
        self.minimum_score = minimum_score

    def retrieve_evidence(self, question):

        # First retrieval attempt
        results = self.retriever.search(
            question,
            top_k=3
        )

        attempts = 1

        sufficient = (
            bool(results)
            and results[0]["relevance_score"]
            >= self.minimum_score
        )

        # Branch: retry with a wider search
        if not sufficient:

            print(
                "Insufficient evidence. "
                "Trying a wider retrieval..."
            )

            results = self.retriever.search(
                question,
                top_k=8
            )

            attempts += 1

        # Final evidence decision
        sufficient = (
            bool(results)
            and results[0]["relevance_score"]
            >= self.minimum_score
        )

        return {
            "evidence": results,
            "sufficient": sufficient,
            "retrieval_attempts": attempts,
        }
