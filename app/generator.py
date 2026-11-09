
import json
from model_services.groq_service import GroqService
import re


class AnswerGenerator:

    def __init__(self):
        self.groq = GroqService()

    def generate(self, question, evidence):

        if not evidence:
            return {
                "status": "refused_correctly",
                "answer": None,
                "citations": []
            }

        context_parts = []
        source_map = {}

        for index, item in enumerate(evidence, start=1):

            source_label = f"S{index}"

            source_map[source_label] = item

            context_parts.append(
                f"""
SOURCE [{source_label}]
Paper: {item['title']}
arXiv: {item['paper_id']}
Version: {item['version']}
PDF page: {item['pdf_page']}

Passage:
{item['text']}
"""
            )

        context = "\n".join(context_parts)

        system_prompt = """
You are a research assistant.

Use ONLY the supplied research passages.

Determine whether the passages contain enough
direct evidence to answer the question.

If sufficient evidence exists:
- Set answerable to true.
- Provide a clear answer.
- Include only source labels that support
  the answer's claims.

If sufficient evidence does not exist:
- Set answerable to false.
- Set answer to an empty string.
- Set used_sources to an empty list.

Never use outside knowledge.
Never invent citations.
Never cite an irrelevant passage.

Return ONLY valid JSON in this exact structure:

{
  "answerable": true,
  "answer": "Your answer with source labels such as [S1].",
  "used_sources": ["S1"]
}

IMPORTANT FORMATTING RULES:
- Return valid JSON only.
- Do not use Markdown code fences.
- Do not use LaTeX notation.
- Avoid backslash characters in the answer.
- Write mathematical expressions in plain text.
- Escape quotation marks inside JSON strings.
"""

        user_prompt = f"""
QUESTION:
{question}

RESEARCH PASSAGES:
{context}
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
            max_tokens=800
        )
        

        if response["status"] != "ok":
            return {
            "status": response["status"],
            "answer": None,
            "citations": [],
            "error": response.get("error"),
            "model": response.get("model"),
            "total_ms": response.get("total_ms"),
            "first_token_ms": response.get("first_token_ms"),
            "tokens_in": response.get("tokens_in"),
            "tokens_out": response.get("tokens_out"),
            "retries": response.get("retries", 0),
            "retry_after_seconds": response.get("retry_after_seconds"),
            "rate_limit_headers": response.get("rate_limit_headers", {})
}

        try:

            raw_json = response["answer"]

            # Escape invalid backslashes inside JSON strings.
            # Preserve valid JSON escape sequences.
            raw_json = re.sub(
                r'\\(?!["\\/bfnrtu])',
                r'\\\\',
                raw_json
            )

            result = json.loads(raw_json)

            if not isinstance(result.get("answerable"), bool):
                raise ValueError("Invalid answerable field")

            if not isinstance(result.get("used_sources"), list):
                raise ValueError("Invalid source list")

            if not result["answerable"]:

                if result["used_sources"]:
                    raise ValueError(
                        "Refusal must not include citations"
                    )

                return {
                    "status": "refused_correctly",
                    "answer": (
                        "The research papers do not contain "
                        "sufficient evidence to answer this question."
                    ),
                    "citations": [],
                    "model": response["model"],
                    "total_ms": response["total_ms"],
                    "tokens_in": response["tokens_in"],
                    "tokens_out": response["tokens_out"]
                }

            answer = result.get("answer", "").strip()

            if not answer:
                raise ValueError("Empty answer")

            used_sources = result["used_sources"]

            if not used_sources:
                raise ValueError(
                    "An answer must have supporting sources"
                )

            if len(set(used_sources)) != len(used_sources):
                raise ValueError("Duplicate source labels")

            citations = []

            for source in used_sources:

                if source not in source_map:
                    raise ValueError(
                        f"Unknown source label: {source}"
                    )

                item = source_map[source]

                citations.append({
                    "chunk_id": item["chunk_id"],
                    "paper_id": item["paper_id"],
                    "title": item["title"],
                    "version": item["version"],
                    "pdf_page": item["pdf_page"],
                    "source_label": source
                })

            return {
                "status": "ok",
                "answer": answer,
                "citations": citations,
                "model": response["model"],
                "total_ms": response["total_ms"],
                "tokens_in": response["tokens_in"],
                "tokens_out": response["tokens_out"]
            }

        except (ValueError, TypeError, json.JSONDecodeError) as error:

            return {
                "status": "validation_failed",
                "answer": None,
                "citations": [],
                "error": str(error),
                "model": response.get("model"),
                "total_ms": response.get("total_ms"),
                "first_token_ms": response.get("first_token_ms"),
                "tokens_in": response.get("tokens_in"),
                "tokens_out": response.get("tokens_out"),
                "retries": response.get("retries", 0)
            }