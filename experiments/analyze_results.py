
import csv
import statistics
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "results" / "results.csv"


def percentile(values, percentile_value):
    """Calculate a percentile using linear interpolation."""

    if not values:
        return None

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * percentile_value / 100
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)

    fraction = position - lower

    return (
        sorted_values[lower]
        + fraction * (sorted_values[upper] - sorted_values[lower])
    )


def analyze_scenario(scenario, rows):
    """Calculate performance metrics for one scenario."""

    total_requests = len(rows)

    latencies = [
        float(row["total_ms"])
        for row in rows
        if row["total_ms"]
    ]

    first_token_latencies = [
        float(row["first_token_ms"])
        for row in rows
        if row["first_token_ms"]
    ]

    successful = sum(row["status"] == "ok" for row in rows)
    rate_limited = sum(row["status"] == "rate_limited" for row in rows)
    timeouts = sum(row["status"] == "timeout" for row in rows)
    errors = sum(row["status"] == "error" for row in rows)

    print(f"\n{'=' * 50}")
    print("Scenario:", scenario)
    print("=" * 50)

    print("Total requests:", total_requests)
    print("Successful:", successful)
    print("Rate limited:", rate_limited)
    print("Timeouts:", timeouts)
    print("Errors:", errors)

    if total_requests:
        print(
            "Success rate:",
            round(successful / total_requests * 100, 2),
            "%"
        )

        print(
            "Rate-limit rate:",
            round(rate_limited / total_requests * 100, 2),
            "%"
        )

        print(
            "Timeout rate:",
            round(timeouts / total_requests * 100, 2),
            "%"
        )

    if latencies:
        print("\nTotal latency (ms):")
        print("p50:", round(percentile(latencies, 50), 2))
        print("p95:", round(percentile(latencies, 95), 2))
        print("p99:", round(percentile(latencies, 99), 2))

    if first_token_latencies:
        print("\nFirst-token latency (ms):")
        print("p50:", round(percentile(first_token_latencies, 50), 2))
        print("p95:", round(percentile(first_token_latencies, 95), 2))
        print("p99:", round(percentile(first_token_latencies, 99), 2))
    else:
        print("\nFirst-token latency: No recorded measurements")


def main():
    if not CSV_FILE.exists():
        print("Results CSV not found:", CSV_FILE)
        return

    grouped_rows = {}

    with open(CSV_FILE, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            scenario = row["scenario"]

            if scenario not in grouped_rows:
                grouped_rows[scenario] = []

            grouped_rows[scenario].append(row)

    if not grouped_rows:
        print("No experiment records found.")
        return

    print("Analyzing:", CSV_FILE)

    for scenario, rows in grouped_rows.items():
        analyze_scenario(scenario, rows)


if __name__ == "__main__":
    main()
