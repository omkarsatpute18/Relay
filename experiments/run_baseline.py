
import time

from app.pipeline import RelayPipeline


QUESTIONS = [
    # Supported research questions
    "How does multi-head attention work?",
    "Why does the Transformer use positional encodings?",
    "How does Moshi support real-time dialogue?",
    "What is the purpose of Inner Monologue in Moshi?",
    "What problem does the Dynamic Chunking paper address?",

    # Unsupported questions
    "What is the capital of Japan?",
    "Who won the FIFA World Cup in 2022?",
    "What is the tallest mountain in the world?",

    # Repeated questions for latency comparison
    "How does multi-head attention work?",
    "How does Moshi support real-time dialogue?"
]


def run_baseline():

    relay = RelayPipeline()

    total = len(QUESTIONS)

    print("\n" + "=" * 60)
    print("THE RELAY - REAL GROQ BASELINE EXPERIMENT")
    print("=" * 60)

    for index, question in enumerate(QUESTIONS, start=1):

        print(f"\nRequest {index}/{total}")
        print("Question:", question)

        result = relay.process(
            question,
            scenario="real_baseline_steady"
        )

        print("Status:", result["status"])
        print("Pipeline latency:", result["total_ms"], "ms")

        if result.get("error"):
            print("Error:", result["error"])

        if index < total:

            retry_after = result.get("retry_after_seconds")

        if retry_after is not None:
            wait_seconds = retry_after + 0.5

            print(
            f"Provider suggested waiting "
            f"{retry_after:.2f} seconds."
        )

        print(
            f"Waiting {wait_seconds:.2f} seconds "
            "including a 0.5-second safety margin..."
        )

        time.sleep(wait_seconds)

    else:
        print("Waiting 2 seconds before next request...")
        time.sleep(2)

    print("\n" + "=" * 60)
    print("BASELINE EXPERIMENT COMPLETED")
    print("=" * 60)

    print("Total requests:", total)
    print("CSV file: results/results.csv")


if __name__ == "__main__":
    run_baseline()
