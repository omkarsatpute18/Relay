
from model_services.groq_service import GroqService


class AnswerGenerator:

    def __init__(self):

        self.groq = GroqService()

    def generate(self, question, evidence):

        if not evidence:

            return {
                "answer": None,
                "citations": [],
                "status": "refused_correctly"
            }

        # Prepare source passages
        context_parts = []
        citations = []

        for index, item in enumerate(
            evidence,
            start=1
        ):

            source_label = f"S{index}"

            context_parts.append(
                f"""
SOURCE [{source_label}]

Paper: {item['title']}
arXiv ID: {item['paper_id']}
Version: {item['version']}
PDF page: {item['pdf_page']}

Passage:
{item['text']}
"""
            )

            citations.append({
                "chunk_id": item["chunk_id"],
                "paper_id": item["paper_id"],
                "title": item["title"],
                "version": item["version"],
                "pdf_page": item["pdf_page"],
                "source_label": source_label
            })

        context = "\n".join(context_parts)

        system_prompt = """
You are The Relay, a research-paper assistant.

STRICT RULES:

1. Answer using only the supplied research passages.
2. Never use outside knowledge or invent facts.
3. Cite supporting sources using [S1], [S2], etc.
4. Use citations next to the claims they support.
5. If the supplied passages do not contain enough
   information, clearly say so.
6. Do not invent paper titles, versions or page numbers.
7. Explain technical concepts clearly.
8. Distinguish direct evidence from interpretation.
"""

        user_prompt = f"""
QUESTION:
{question}

RETRIEVED RESEARCH PASSAGES:
{context}

Write a clear answer to the question using only
the supplied passages. Include source labels.
"""

        response = self.groq.generate(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=500
        )

        if response["status"] != "ok":

            return {
                "answer": None,
                "citations": [],
                "status": response["status"],
                "error": response["error"]
            }

        return {
            "answer": response["answer"],
            "citations": citations,
            "status": "ok",
            "model": response["model"],
            "total_ms": response["total_ms"],
            "tokens_in": response["tokens_in"],
            "tokens_out": response["tokens_out"]
        }
