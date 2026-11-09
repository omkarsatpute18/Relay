
import sys
import time
import uuid
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Make the project root accessible.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_services.standin_service import StandinService, StandinConfig
from app.csv_logger import CSVLogger

logger = CSVLogger()

def run_one_request(service, request_number, scenario):
    """Run one simulated request and collect measurements."""

    start_time = time.perf_counter()

    result = service.generate(
        f"Explain attention mechanism. Request {request_number}"
    )

    total_ms = (time.perf_counter() - start_time) * 1000

    from datetime import datetime, timezone

    logger.log_request(
        scenario=scenario,
        source="standin",
        start_time=datetime.now(timezone.utc).isoformat(),
        first_token_ms=None,
        total_ms=round(total_ms, 2),
        status=result["status"],
        retries=0,
        tokens_in=None,
        tokens_out=None,
        retrieval_setting="standin_direct",
        answer_grade=""
    )

    return result


def run_scenario(name, request_count, workers, config):
    """Run one stand-in load scenario."""

    print(f"\nStarting scenario: {name}")

    service = StandinService(config)

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(run_one_request, service, i + 1, name)
            for i in range(request_count)
        ]

        results = [future.result() for future in futures]

    duration = time.perf_counter() - start_time

    successful = sum(r["status"] == "ok" for r in results)
    rate_limited = sum(r["status"] == "rate_limited" for r in results)
    timed_out = sum(r["status"] == "timeout" for r in results)
    errors = sum(r["status"] == "error" for r in results)

    metrics = service.get_metrics()

    print("Requests:", request_count)
    print("Duration:", round(duration, 2), "seconds")
    print("Successful:", successful)
    print("Rate limited:", rate_limited)
    print("Timeouts:", timed_out)
    print("Errors:", errors)
    print("Peak queue length:", metrics["peak_queue_length"])

    return {
        "scenario": name,
        "requests": request_count,
        "duration_seconds": round(duration, 2),
        "successful": successful,
        "rate_limited": rate_limited,
        "timeouts": timed_out,
        "errors": errors,
        "peak_queue_length": metrics["peak_queue_length"]
    }


def main():
    scenarios = [
        {
            "name": "standin_steady",
            "requests": 10,
            "workers": 1,
            "config": StandinConfig(
                base_latency=0.5,
                max_concurrent_requests=3
            )
        },
        {
            "name": "standin_burst",
            "requests": 20,
            "workers": 10,
            "config": StandinConfig(
                base_latency=0.5,
                max_concurrent_requests=3
            )
        },
        {
            "name": "standin_overload",
            "requests": 30,
            "workers": 20,
            "config": StandinConfig(
                base_latency=0.5,
                max_concurrent_requests=3,
                failure_rate=0.05,
                rate_limit_rate=0.10
            )
        }
    ]

    all_results = []

    for scenario in scenarios:
        result = run_scenario(
            scenario["name"],
            scenario["requests"],
            scenario["workers"],
            scenario["config"]
        )
        all_results.append(result)

    print("\n========== FINAL SUMMARY ==========")

    for result in all_results:
        print(result)


if __name__ == "__main__":
    main()
