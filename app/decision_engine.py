
class DecisionEngine:

    def __init__(
        self,
        retriever,
        minimum_score=1.0
    ):
        self.retriever = retriever
        self.minimum_score = minimum_score

    def retrieve_evidence(
        self,
        question,
        retrieval_setting="adaptive_top3_top8"
    ):

        attempts = 1

        # Fixed retrieval: Top 3
        if retrieval_setting == "bm25_top3":
            results = self.retriever.search(
                question,
                top_k=3
            )

        # Fixed retrieval: Top 5
        elif retrieval_setting == "bm25_top5":
            results = self.retriever.search(
                question,
                top_k=5
            )

        # Fixed retrieval: Top 8
        elif retrieval_setting == "bm25_top8":
            results = self.retriever.search(
                question,
                top_k=8
            )

        # Original adaptive retrieval strategy
        elif retrieval_setting == "adaptive_top3_top8":

            results = self.retriever.search(
                question,
                top_k=3
            )

            sufficient = (
                bool(results)
                and results[0]["relevance_score"]
                >= self.minimum_score
            )

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

        else:
            raise ValueError(
                f"Unknown retrieval setting: {retrieval_setting}"
            )

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
            "retrieval_setting": retrieval_setting
        }
