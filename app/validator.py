
class CitationValidator:

    def validate(self, generated_response, evidence):

        citations = generated_response.get(
            "citations", []
        )

        evidence_map = {
            item["chunk_id"]: item
            for item in evidence
        }

        if not citations:
            return {
                "valid": False,
                "reason": "No citations provided."
            }

        for citation in citations:

            chunk_id = citation.get("chunk_id")

            if chunk_id not in evidence_map:
                return {
                    "valid": False,
                    "reason": (
                        f"Unknown evidence chunk: {chunk_id}"
                    )
                }

            original = evidence_map[chunk_id]

            if (
                citation.get("paper_id")
                != original["paper_id"]
                or citation.get("pdf_page")
                != original["pdf_page"]
                or citation.get("version")
                != original["version"]
            ):

                return {
                    "valid": False,
                    "reason": (
                        "Citation metadata does not "
                        "match the retrieved passage."
                    )
                }

        return {
            "valid": True,
            "reason": "All citation references are valid."
        }
