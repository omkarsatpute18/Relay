
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_services.standin_service import StandinService, StandinConfig
from app.csv_logger import CSVLogger

logger = CSVLogger()

# Generate one unique ID for this complete experiment run.
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def run_one_request(service, request_number, scenario):
    """Run a normal request with failure and rate-limit simulation."""

    request_start_time = time.perf_counter()
    start_timestamp = datetime.now(timezone.utc).isoformat()

    result = service.generate(
        f"Explain attention mechanism. Request {request_number}"
    )

    total_ms = (time.perf_counter() - request_start_time) * 1000

    logger.log_request(
        scenario=scenario,
        source="standin",
        start_time=start_timestamp,
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



def run_streaming_request(service, request_number, scenario):
    """Run a streaming request and record its actual status."""

    request_start_time = time.perf_counter()
    start_timestamp = datetime.now(timezone.utc).isoformat()

    first_token_ms = None
    response_parts = []
    status = "ok"
    error = None
    retries = 0

    for chunk in service.generate_stream(
        f"Explain attention mechanism. Request {request_number}"
    ):
        if chunk["status"] != "ok":
            status = chunk["status"]
            error = chunk.get("error")
            break

        if first_token_ms is None:
            first_token_ms = chunk["first_token_ms"]

        response_parts.append(chunk["piece"])

    total_ms = (time.perf_counter() - request_start_time) * 1000

    result = {
        "status": status,
        "answer": "".join(response_parts) if status == "ok" else None,
        "total_ms": round(total_ms, 2),
        "first_token_ms": first_token_ms,
        "error": error
    }

    logger.log_request(
        scenario=scenario,
        source="standin",
        start_time=start_timestamp,
        first_token_ms=first_token_ms,
        total_ms=round(total_ms, 2),
        status=status,
        retries=retries,
        tokens_in=None,
        tokens_out=None,
        retrieval_setting="standin_streaming",
        answer_grade=""
    )

    return result


def run_scenario(name, request_count, workers, config, streaming=False):
    """Run one normal or streaming load scenario."""

    print(f"\nStarting scenario: {name}")

    service = StandinService(config)
    start_time = time.perf_counter()

    request_function = (
        run_streaming_request if streaming else run_one_request
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                request_function,
                service,
                i + 1,
                name
            )
            for i in range(request_count)
        ]

        results = [future.result() for future in futures]

    duration = time.perf_counter() - start_time

    successful = sum(r["status"] == "ok" for r in results)
    rate_limited = sum(
        r["status"] == "rate_limited" for r in results
    )
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

    if streaming:
        first_token_values = [
            r["first_token_ms"]
            for r in results
            if r.get("first_token_ms") is not None
        ]

        if first_token_values:
            print(
                "Average first-token latency:",
                round(
                    sum(first_token_values) / len(first_token_values),
                    2
                ),
                "ms"
            )

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
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.5,
                max_concurrent_requests=3
            )
        },
        {
            "name": "standin_burst",
            "requests": 20,
            "workers": 10,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.5,
                max_concurrent_requests=3
            )
        },
        {
            "name": "standin_overload",
            "requests": 30,
            "workers": 20,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.5,
                max_concurrent_requests=3,
                failure_rate=0.05,
                rate_limit_rate=0.10
            )
        },
        {
            "name": "standin_streaming",
            "requests": 10,
            "workers": 3,
            "streaming": True,
            "config": StandinConfig(
                stream_piece_delay=0.1,
                max_concurrent_requests=3
            )
        },
        {
            "name": "standin_half_rpm",
            "requests": 10,
            "workers": 1,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.1,
                max_concurrent_requests=3,
                requests_per_minute=5,
                rate_limit_window_seconds=60,
                failure_rate=0.0,
                timeout_rate=0.0,
                rate_limit_rate=0.0
            )
        },
        {
    "name": "standin_daily_exhausted",
    "requests": 10,
    "workers": 1,
    "streaming": False,
    "config": StandinConfig(
        base_latency=0.1,
        max_concurrent_requests=3,
        requests_per_day=5,
        daily_window_seconds=86400,
        failure_rate=0.0,
        timeout_rate=0.0,
        rate_limit_rate=0.0
    )
},
    ]

    all_results = []

    for scenario in scenarios:

        unique_scenario_name = f"{scenario['name']}_{RUN_ID}"

        result = run_scenario(
            name=unique_scenario_name,
            request_count=scenario["requests"],
            workers=scenario["workers"],
            config=scenario["config"],
            streaming=scenario["streaming"]
        )

        all_results.append(result)

    print("\n========== FINAL SUMMARY ==========")

    for result in all_results:
        print(result)


if __name__ == "__main__":
    main()
