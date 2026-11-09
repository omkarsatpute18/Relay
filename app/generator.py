
class AnswerGenerator:

    def generate(self, question, evidence):

        if not evidence:
            return {
                "answer": (
                    "I could not find sufficient "
                    "evidence in the research library."
                ),
                "citations": []
            }

        answer_parts = []
        citations = []

        for index, item in enumerate(
            evidence[:3],
            start=1
        ):

            citation = {
                "chunk_id": item["chunk_id"],
                "paper_id": item["paper_id"],
                "title": item["title"],
                "version": item["version"],
                "pdf_page": item["pdf_page"]
            }

            answer_parts.append(
                f"Evidence {index}: {item['text']}"
            )

            citations.append(citation)

        answer = (
            "The following passages from the "
            "research papers are relevant to "
            f"your question: {question}\n\n"
            + "\n\n".join(answer_parts)
        )

        return {
            "answer": answer,
            "citations": citations
        }
