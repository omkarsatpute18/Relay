
import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi


ROOT_DIR = Path(__file__).resolve().parent.parent

CHUNKS_FILE = ROOT_DIR / "results" / "paper_chunks.json"


def tokenize(text):
    """
    Convert text into lowercase searchable terms.
    """

    return re.findall(
        r"\b[a-z0-9]+\b",
        text.lower()
    )


class PaperRetriever:

    def __init__(self, chunks_file=CHUNKS_FILE):

        if not chunks_file.exists():
            raise FileNotFoundError(
                "paper_chunks.json not found. "
                "Run ingestion first."
            )

        with open(
            chunks_file,
            "r",
            encoding="utf-8"
        ) as file:

            self.chunks = json.load(file)

        if not self.chunks:
            raise ValueError("No paper chunks found.")

        # Prepare documents for BM25
        self.tokenized_documents = [
            tokenize(chunk["text"])
            for chunk in self.chunks
        ]

        # Build search index
        self.bm25 = BM25Okapi(
            self.tokenized_documents
        )

        print(
            f"Retriever initialized with "
            f"{len(self.chunks)} chunks."
        )

    def search(self, query, top_k=5):

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        scores = self.bm25.get_scores(
            query_tokens
        )

        # Rank chunks by relevance score
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )

        results = []

        for index in ranked_indices:

            if len(results) >= top_k:
                break

            score = float(scores[index])

            # Ignore zero-relevance passages
            if score <= 0:
                continue

            chunk = self.chunks[index]

            results.append({
                "chunk_id": chunk["chunk_id"],
                "paper_id": chunk["paper_id"],
                "title": chunk["title"],
                "version": chunk["version"],
                "pdf_page": chunk["pdf_page"],
                "relevance_score": round(score, 4),
                "text": chunk["text"]
            })

        return results


if __name__ == "__main__":

    retriever = PaperRetriever()

    while True:

        query = input(
            "\nEnter your research question "
            "(or type exit): "
        )

        if query.lower().strip() == "exit":
            break

        results = retriever.search(
            query,
            top_k=5
        )

        if not results:
            print("\nNo relevant passages found.")
            continue

        print("\nRETRIEVED PASSAGES")
        print("=" * 60)

        for result in results:

            print("\nPaper:", result["title"])
            print("arXiv:", result["paper_id"])
            print("Version:", result["version"])
            print("PDF page:", result["pdf_page"])
            print("Score:", result["relevance_score"])

            print("\nPassage:")
            print(result["text"])

            print("-" * 60)
