
import csv
from pathlib import Path
from collections import defaultdict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = PROJECT_ROOT / "results" / "results.csv"


def percentile(values, percentile_value):
    """Calculate percentile using linear interpolation."""

    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * percentile_value / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return values[lower] + fraction * (
        values[upper] - values[lower]
    )


def analyze_scenario(scenario, rows):

    total = len(rows)

    successful_rows = [
        row for row in rows if row["status"] == "ok"
    ]

    latencies = [
        float(row["total_ms"])
        for row in successful_rows
        if row["total_ms"]
    ]

    first_token_latencies = [
        float(row["first_token_ms"])
        for row in successful_rows
        if row["first_token_ms"]
    ]

    successful = len(successful_rows)
    rate_limited = sum(
        row["status"] == "rate_limited" for row in rows
    )
    timeouts = sum(
        row["status"] == "timeout" for row in rows
    )
    errors = sum(
        row["status"] == "error" for row in rows
    )

    print("\n" + "=" * 55)
    print("Scenario:", scenario)
    print("=" * 55)

    print("Total requests:", total)
    print("Successful:", successful)
    print("Rate limited:", rate_limited)
    print("Timeouts:", timeouts)
    print("Errors:", errors)

    if total:
        print(
            "Success rate:",
            round(successful / total * 100, 2), "%"
        )
        print(
            "Rate-limit rate:",
            round(rate_limited / total * 100, 2), "%"
        )
        print(
            "Timeout rate:",
            round(timeouts / total * 100, 2), "%"
        )
        print(
            "Error rate:",
            round(errors / total * 100, 2), "%"
        )

    if latencies:
        print("\nSuccessful total latency (ms):")
        print("Sample count:", len(latencies))
        print("p50:", round(percentile(latencies, 50), 2))
        print("p95:", round(percentile(latencies, 95), 2))
        print("p99:", round(percentile(latencies, 99), 2))

    if first_token_latencies:
        print("\nFirst-token latency (ms):")
        print("Sample count:", len(first_token_latencies))
        print("p50:", round(percentile(first_token_latencies, 50), 2))
        print("p95:", round(percentile(first_token_latencies, 95), 2))
        print("p99:", round(percentile(first_token_latencies, 99), 2))
    else:
        print("\nFirst-token latency: No recorded measurements")


def main():

    if not CSV_FILE.exists():
        print("Results CSV not found:", CSV_FILE)
        return

    grouped_rows = defaultdict(list)

    with open(CSV_FILE, "r", newline="", encoding="utf-8") as file:

        reader = csv.DictReader(file)

        for row in reader:

            scenario = row["scenario"]

            # Exclude the manually inserted logger test.
            if scenario == "logger_test":
                continue

            # Keep every unique timestamped run separate.
            grouped_rows[scenario].append(row)

    if not grouped_rows:
        print("No experiment records found.")
        return

    print("Analyzing:", CSV_FILE)

    for scenario, rows in grouped_rows.items():
        analyze_scenario(scenario, rows)


if __name__ == "__main__":
    main()
