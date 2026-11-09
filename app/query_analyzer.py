
import re


def analyze_query(question: str) -> dict:
    """
    Analyze the user's question and prepare
    information for the retrieval engine.
    """

    question = question.strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        question.lower()
    )

    if question.endswith("?"):
        question_type = "factual"
    elif any(
        word in words
        for word in ["explain", "describe", "discuss"]
    ):
        question_type = "explanatory"
    elif any(
        word in words
        for word in ["compare", "difference", "versus"]
    ):
        question_type = "comparative"
    else:
        question_type = "general"

    return {
        "original_question": question,
        "search_query": question,
        "question_type": question_type,
        "keywords": words,
    }


if __name__ == "__main__":

    question = input("Enter your question: ")

    result = analyze_query(question)

    print("\nQUERY ANALYSIS")
    print("=" * 40)

    for key, value in result.items():
        print(f"{key}: {value}")
