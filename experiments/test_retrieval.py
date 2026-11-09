
from app.retriever import PaperRetriever


def main():

    retriever = PaperRetriever()

    questions = [
        "How does multi-head attention work?",
        "What is positional encoding?",
        "How does Moshi perform real-time dialogue?",
        "What is the role of speech and text in Moshi?",
        "Explain dynamic chunking in hierarchical sequence modeling."
    ]

    for question in questions:

        print("\n" + "=" * 70)
        print("QUESTION:", question)
        print("=" * 70)

        results = retriever.search(
            question,
            top_k=3
        )

        if not results:
            print("No relevant passages found.")
            continue

        for rank, result in enumerate(
            results,
            start=1
        ):

            print(f"\nRank: {rank}")
            print("Paper:", result["title"])
            print("PDF page:", result["pdf_page"])
            print("Score:", result["relevance_score"])
            print("Passage:", result["text"][:500])


if __name__ == "__main__":
    main()
