
from model_services.groq_service import GroqService


def run_test(name, responses, expected_status, expected_retries):
    service = GroqService.__new__(GroqService)

    call_count = {"value": 0}

    def fake_generate(messages, max_tokens=800):
        result = responses[call_count["value"]]
        call_count["value"] += 1
        return result.copy()

    service.generate = fake_generate

    result = service.generate_with_retries(
        messages=[],
        max_attempts=3,
        max_retry_wait_seconds=2,
        base_backoff_seconds=0.1
    )

    print(f"\n{name}")
    print("Final status:", result["status"])
    print("Retries:", result["retries"])
    print("Total calls:", call_count["value"])

    assert result["status"] == expected_status
    assert result["retries"] == expected_retries

    print("Test passed!")


def main():

    # Test 1: Rate limit followed by success.
    run_test(
        "TEST 1: Rate limit followed by success",
        [
            {
                "status": "rate_limited",
                "retry_after_seconds": 0.1
            },
            {
                "status": "ok",
                "answer": "Successful answer"
            }
        ],
        "ok",
        1
    )

    # Test 2: Temporary service error followed by success.
    run_test(
        "TEST 2: Temporary error followed by success",
        [
            {
                "status": "error",
                "retryable": True
            },
            {
                "status": "ok",
                "answer": "Successful answer"
            }
        ],
        "ok",
        1
    )

    # Test 3: Daily budget exhausted.
    # The retry delay exceeds our configured wait budget.
    run_test(
        "TEST 3: Daily budget exhausted",
        [
            {
                "status": "rate_limited",
                "retry_after_seconds": 86399,
                "limit_type": "daily"
            }
        ],
        "rate_limited",
        0
    )


if __name__ == "__main__":
    main()
