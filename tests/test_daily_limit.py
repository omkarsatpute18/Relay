
from model_services.standin_service import (
    StandinService,
    StandinConfig
)


def main():
    config = StandinConfig(
        base_latency=0.1,
        max_concurrent_requests=3,
        requests_per_day=5,
        daily_window_seconds=86400
    )

    service = StandinService(config)

    print("Testing a daily allowance of 5 requests\n")

    for i in range(1, 8):
        result = service.generate(f"Daily budget test {i}")

        print(
            f"Request {i}: "
            f"Status = {result['status']}, "
            f"Limit = {result.get('limit_type', 'N/A')}, "
            f"Retry after = "
            f"{result.get('retry_after_seconds', 'N/A')} seconds"
        )

    print("\nFinal metrics:")
    print(service.get_metrics())


if __name__ == "__main__":
    main()
