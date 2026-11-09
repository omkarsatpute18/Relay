import time

from app.pipeline import RelayPipeline


# Time between independent requests.
INTER_REQUEST_DELAY_SECONDS = 2.0


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
]


def main():
    relay = RelayPipeline()

    total_requests = len(QUESTIONS)

    successful = 0
    rate_limited = 0
    timeouts = 0
    errors = 0
    total_retries = 0

    print("=" * 60)
    print("THE RELAY - REAL GROQ BASELINE EXPERIMENT")
    print("=" * 60)

    print(f"Total requests: {total_requests}")
    print(f"Delay between requests: {INTER_REQUEST_DELAY_SECONDS} seconds")
    print()

    experiment_start = time.perf_counter()

    for index, question in enumerate(QUESTIONS, start=1):

        print("-" * 60)
        print(f"Request {index}/{total_requests}")
        print(f"Question: {question}")

        result = relay.process(
            question=question,
            scenario="real_baseline_retry",
        )

        status = result.get("status", "error")
        retries = result.get("retries", 0)
        total_ms = result.get("total_ms", 0)

        total_retries += retries

        # Count successful service requests separately from answer quality.
        if status in {"ok", "refused_correctly"}:
            successful += 1
        elif status == "rate_limited":
            rate_limited += 1
        elif status == "timeout":
            timeouts += 1
        else:
            errors += 1

        print(f"Status: {status}")
        print(f"Pipeline time: {total_ms:.2f} ms")
        print(f"Retries: {retries}")

        if result.get("tokens_in") is not None:
            print(f"Input tokens: {result['tokens_in']}")

        if result.get("tokens_out") is not None:
            print(f"Output tokens: {result['tokens_out']}")

        if result.get("first_token_ms") is not None:
            print(
                f"First token time: "
                f"{result['first_token_ms']:.2f} ms"
            )

        if result.get("answer"):
            print(f"Answer: {result['answer']}")

        if result.get("citations"):
            print("Citations:")

            for citation in result["citations"]:
                print(citation)

        if result.get("error"):
            print(f"Error: {result['error']}")

        if status == "rate_limited":
            retry_after = result.get("retry_after_seconds")

            if retry_after is not None:
                print(
                    f"Provider suggested retry after: "
                    f"{retry_after} seconds"
                )

        # Keep a consistent delay between independent requests.
        # The retry wrapper handles retries within each request.
        if index < total_requests:
            print(
                f"Waiting {INTER_REQUEST_DELAY_SECONDS} seconds "
                "before the next request..."
            )
            time.sleep(INTER_REQUEST_DELAY_SECONDS)

    experiment_duration = time.perf_counter() - experiment_start

    print()
    print("=" * 60)
    print("BASELINE EXPERIMENT SUMMARY")
    print("=" * 60)

    print(f"Total requests: {total_requests}")
    print(f"Successful service requests: {successful}")
    print(f"Rate-limited requests: {rate_limited}")
    print(f"Timed-out requests: {timeouts}")
    print(f"Other errors: {errors}")
    print(f"Total retries: {total_retries}")
    print(f"Experiment duration: {experiment_duration:.2f} seconds")

    if experiment_duration > 0:
        request_rate = total_requests / experiment_duration
        print(f"Average offered rate: {request_rate:.2f} requests/second")

    print()
    print("Results saved in: results/results.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()