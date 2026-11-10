
from app.retriever import PaperRetriever
from app.decision_engine import DecisionEngine

retriever = PaperRetriever()

engine = DecisionEngine(
    retriever=retriever,
    minimum_score=1.0
)

question = "How does multi-head attention work?"

settings = [
    "bm25_top3",
    "bm25_top5",
    "bm25_top8",
    "adaptive_top3_top8"
]

for setting in settings:

    print(f"\n===== {setting} =====")

    result = engine.retrieve_evidence(
        question,
        retrieval_setting=setting
    )

    print("Evidence sufficient:", result["sufficient"])
    print("Retrieval attempts:", result["retrieval_attempts"])
    print("Chunks returned:", len(result["evidence"]))

    for chunk in result["evidence"]:
        print(
            f"Chunk: {chunk['chunk_id']} | "
            f"Page: {chunk['pdf_page']} | "
            f"Score: {chunk['relevance_score']}"
        )
