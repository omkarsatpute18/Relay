
class CitationValidator:

    def validate(self, generated_response, evidence):

        citations = generated_response.get("citations", [])

        if not citations:
            return {
                "valid": False,
                "reason": "No citations provided."
            }

        evidence_map = {
            item["chunk_id"]: item
            for item in evidence
        }

        required_fields = [
            "chunk_id",
            "paper_id",
            "pdf_page",
            "version"
        ]

        for citation in citations:

            for field in required_fields:
                if field not in citation:
                    return {
                        "valid": False,
                        "reason": f"Missing citation field: {field}"
                    }

            chunk_id = citation["chunk_id"]

            if chunk_id not in evidence_map:
                return {
                    "valid": False,
                    "reason": f"Unknown evidence chunk: {chunk_id}"
                }

            original = evidence_map[chunk_id]

            for field in required_fields:
                if citation[field] != original[field]:
                    return {
                        "valid": False,
                        "reason": (
                            f"Citation {field} does not match "
                            "the retrieved passage."
                        )
                    }

        return {
            "valid": True,
            "reason": "All citation references and metadata are valid."
        }
