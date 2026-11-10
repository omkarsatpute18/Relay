import sys
import time
import statistics
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from model_services.standin_service import StandinService, StandinConfig
from app.csv_logger import CSVLogger

logger = CSVLogger()
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def percentile(values, percentile_value):
    """Calculate a nearest-rank percentile without extra dependencies."""
    if not values:
        return None

    ordered = sorted(values)
    rank = max(1, int((percentile_value / 100) * len(ordered) + 0.999999))
    return round(ordered[min(rank - 1, len(ordered) - 1)], 2)


def log_result(
    scenario,
    start_timestamp,
    total_ms,
    status,
    first_token_ms=None,
    answer_grade="",
):
    # CSV status remains within the assignment's allowed status vocabulary.
    logger.log_request(
        scenario=scenario,
        source="standin",
        start_time=start_timestamp,
        first_token_ms=first_token_ms,
        total_ms=round(total_ms, 2),
        status=status,
        retries=0,
        tokens_in=None,
        tokens_out=None,
        retrieval_setting="standin_direct",
        answer_grade=answer_grade,
    )


def run_one_request(service, request_number, scenario):
    start = time.perf_counter()
    start_timestamp = datetime.now(timezone.utc).isoformat()

    result = service.generate(
        f"Explain attention mechanism. Request {request_number}"
    )

    total_ms = (time.perf_counter() - start) * 1000
    answer_grade = (
        "refused_correctly" if result.get("outcome") == "refused" else ""
    )

    log_result(
        scenario=scenario,
        start_timestamp=start_timestamp,
        total_ms=total_ms,
        status=result["status"],
        answer_grade=answer_grade,
    )

    # Use caller-observed wall-clock duration for reporting. A quota rejection
    # may have an internal service duration of 0 ms, but the caller still
    # spends a measurable amount of time making that request.
    result["measured_total_ms"] = round(total_ms, 2)
    result["total_ms"] = round(total_ms, 2)
    return result


def run_streaming_request(service, request_number, scenario):
    start = time.perf_counter()
    start_timestamp = datetime.now(timezone.utc).isoformat()

    first_token_ms = None
    response_parts = []
    status = "ok"
    error = None
    outcome = "answered"

    for chunk in service.generate_stream(
        f"Explain attention mechanism. Request {request_number}"
    ):
        if chunk["status"] != "ok":
            status = chunk["status"]
            error = chunk.get("error")
            outcome = chunk.get("outcome", "")
            break

        if first_token_ms is None:
            first_token_ms = chunk.get("first_token_ms")

        response_parts.append(chunk["piece"])
        outcome = chunk.get("outcome", outcome)

    total_ms = (time.perf_counter() - start) * 1000
    answer_grade = "refused_correctly" if outcome == "refused" else ""

    log_result(
        scenario=scenario,
        start_timestamp=start_timestamp,
        total_ms=total_ms,
        status=status,
        first_token_ms=first_token_ms,
        answer_grade=answer_grade,
    )

    return {
        "status": status,
        "answer": "".join(response_parts) if status == "ok" else None,
        "total_ms": round(total_ms, 2),
        "first_token_ms": first_token_ms,
        "error": error,
        "outcome": outcome,
    }


def run_scenario(name, request_count, workers, config, streaming=False):
    print(f"\nStarting scenario: {name}")

    service = StandinService(config)
    scenario_start = time.perf_counter()

    request_function = (
        run_streaming_request if streaming else run_one_request
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(request_function, service, i + 1, name)
            for i in range(request_count)
        ]
        results = [future.result() for future in futures]

    duration = time.perf_counter() - scenario_start

    successful = sum(r["status"] == "ok" for r in results)
    rate_limited = sum(r["status"] == "rate_limited" for r in results)
    timed_out = sum(r["status"] == "timeout" for r in results)
    errors = sum(r["status"] == "error" for r in results)
    refusals = sum(r.get("outcome") == "refused" for r in results)

    metrics = service.get_metrics()
    total_values = [
        r.get("measured_total_ms", r.get("total_ms"))
        for r in results
        if r.get("measured_total_ms", r.get("total_ms")) is not None
    ]
    first_token_values = [
        r["first_token_ms"]
        for r in results
        if r.get("first_token_ms") is not None
    ]

    # Requests are submitted together as a batch. This is achieved throughput,
    # not a paced offered-arrival rate.
    throughput_rate = request_count / duration if duration > 0 else 0

    print("Requests:", request_count)
    print("Workers:", workers)
    print("Duration:", round(duration, 2), "seconds")
    print("Completed throughput:", round(throughput_rate, 3), "requests/second")
    print("Workload pattern: batch submission (not paced arrivals)")
    print("Successful service responses:", successful)
    print("Rate limited:", rate_limited)
    print("Timeouts:", timed_out)
    print("Errors:", errors)
    print("Model refusals:", refusals)
    print("Peak queue length:", metrics["peak_queue_length"])
    print("Peak in-flight requests:", metrics["peak_in_flight"])

    print(
        "Total latency p50/p95/p99 (ms):",
        percentile(total_values, 50),
        percentile(total_values, 95),
        percentile(total_values, 99),
    )

    if first_token_values:
        print(
            "First-token latency p50/p95/p99 (ms):",
            percentile(first_token_values, 50),
            percentile(first_token_values, 95),
            percentile(first_token_values, 99),
        )
    else:
        print("First-token latency: not measured for non-streaming scenario")

    return {
        "scenario": name,
        "requests": request_count,
        "workers": workers,
        "duration_seconds": round(duration, 2),
        "completed_throughput_requests_per_second": round(throughput_rate, 3),
        "arrival_pattern": "batch_submission",
        "successful": successful,
        "rate_limited": rate_limited,
        "timeouts": timed_out,
        "errors": errors,
        "refusals": refusals,
        "peak_queue_length": metrics["peak_queue_length"],
        "peak_in_flight": metrics["peak_in_flight"],
        "total_p50_ms": percentile(total_values, 50),
        "total_p95_ms": percentile(total_values, 95),
        "total_p99_ms": percentile(total_values, 99),
        "first_token_p50_ms": percentile(first_token_values, 50),
        "first_token_p95_ms": percentile(first_token_values, 95),
        "first_token_p99_ms": percentile(first_token_values, 99),
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
                max_concurrent_requests=3,
            ),
        },
        {
            "name": "standin_burst",
            "requests": 20,
            "workers": 10,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.5,
                extra_load_latency=0.25,
                max_concurrent_requests=3,
            ),
        },
        {
            "name": "standin_overload",
            "requests": 30,
            "workers": 20,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.5,
                extra_load_latency=0.3,
                max_concurrent_requests=3,
                failure_rate=0.05,
                rate_limit_rate=0.10,
                timeout_rate=0.05,
            ),
        },
        {
            "name": "standin_refusal",
            "requests": 10,
            "workers": 3,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.2,
                max_concurrent_requests=3,
                refusal_rate=0.30,
            ),
        },
        {
            "name": "standin_streaming",
            "requests": 10,
            "workers": 3,
            "streaming": True,
            "config": StandinConfig(
                base_latency=0.2,
                stream_piece_delay=0.1,
                max_concurrent_requests=3,
            ),
        },
        {
            # Synthetic demonstration: baseline 10 RPM, then halve to 5 RPM.
            # This is not a claim about Groq's actual RPM limit.
            "name": "standin_half_rpm",
            "requests": 10,
            "workers": 1,
            "streaming": False,
            "config": StandinConfig(
                base_latency=0.1,
                max_concurrent_requests=3,
                requests_per_minute=5,
                rate_limit_window_seconds=60,
            ),
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
            ),
        },
    ]

    all_results = []

    for scenario in scenarios:
        unique_name = f"{scenario['name']}_{RUN_ID}"
        result = run_scenario(
            name=unique_name,
            request_count=scenario["requests"],
            workers=scenario["workers"],
            config=scenario["config"],
            streaming=scenario["streaming"],
        )
        all_results.append(result)

    print("\n========== FINAL SUMMARY ==========")
    for result in all_results:
        print(result)


if __name__ == "__main__":
    main()
