
from model_services.standin_service import (
    StandinService,
    StandinConfig
)


def main():
    config = StandinConfig(
        base_latency=0.1,
        max_concurrent_requests=3,
        requests_per_minute=5,
        rate_limit_window_seconds=60
    )

    service = StandinService(config)

    print("Testing a limit of 5 requests per minute\n")

    for i in range(1, 8):
        result = service.generate(f"Test prompt {i}")

        print(
            f"Request {i}: "
            f"Status = {result['status']}, "
            f"Retry after = "
            f"{result.get('retry_after_seconds', 'N/A')} seconds"
        )

    print("\nFinal metrics:")
    print(service.get_metrics())


if __name__ == "__main__":
    main()
