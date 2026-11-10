
from app.pipeline import RelayPipeline


QUESTIONS = [
    "What is the main idea behind the Transformer architecture?",
    "How does multi-head attention work?",
    "What is the role of positional encoding in Transformers?",
    "How does Moshi support real-time dialogue?",
    "What is the purpose of Inner Monologue in Moshi?",
    "How does dynamic chunking work in hierarchical sequence modeling?",
    "What problem does dynamic chunking try to address?",
    "What is the capital of Japan?",
    "Who won the FIFA World Cup in 2022?",
    "Explain the difference between CNNs and RNNs.",
    "Why does the Transformer scale dot-product attention by the square root of the key dimension?",
    "How do recurrent, convolutional, and self-attention layers compare in sequential operations and maximum path length?",
    "What does Inner Monologue add to Moshi, and how does it support streaming speech recognition and speech generation?",
    "How does the routing module identify chunk boundaries, and what does the downsampler do?",
    "What is the current USD to INR exchange rate?"
]


def main():
    print("\n===== RELAY 15-QUESTION EVALUATION =====")

    for i, question in enumerate(QUESTIONS, start=1):
        print(f"{i}. {question}")

    try:
        question_number = int(input("\nEnter question number to run (1-15): "))

        if question_number < 1 or question_number > 15:
            print("Please enter a number between 1 and 15.")
            return

        question = QUESTIONS[question_number - 1]

        print(f"\nRunning Question {question_number}...")
        print("Question:", question)

        relay = RelayPipeline()
        result = relay.process(
            question,
            scenario="retrieval_comparison",
            retrieval_setting="bm25_top8"
        )

        print("\n===== RESULT =====")
        print("Status:", result.get("status"))
        print("Answer:", result.get("answer", "No answer returned."))
        print("Citations:", result.get("citations", []))
        print("Total time (ms):", result.get("total_ms"))
        print("First token time (ms):", result.get("first_token_ms"))
        print("Retries:", result.get("retries"))
        print("Input tokens:", result.get("tokens_in"))
        print("Output tokens:", result.get("tokens_out"))

        if result.get("error"):
            print("Error:", result.get("error"))

        print("\nThe result has been logged to results/results.csv.")

    except ValueError:
        print("Invalid input. Please enter a number from 1 to 15.")


if __name__ == "__main__":
    main()
