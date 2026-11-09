
import time
import random
import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class StandinConfig:
    base_latency: float = 1.0
    extra_load_latency: float = 0.5
    max_concurrent_requests: int = 3
    failure_rate: float = 0.0
    timeout_rate: float = 0.0
    rate_limit_rate: float = 0.0
    stream_piece_delay: float = 0.1

    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None

    rate_limit_window_seconds: float = 60.0
    daily_window_seconds: float = 86400.0


class StandinService:
    def __init__(self, config=None):
        self.config = config or StandinConfig()

        self.semaphore = threading.Semaphore(
            self.config.max_concurrent_requests
        )

        self.active_requests = 0
        self.waiting_requests = 0
        self.peak_queue_length = 0

        self.lock = threading.Lock()
        self.rate_limit_lock = threading.Lock()

        self.minute_timestamps = deque()
        self.daily_timestamps = deque()

    def _check_request_quota(self):
        """Atomically check and reserve both request quotas."""

        now = time.monotonic()

        minute_limit = self.config.requests_per_minute
        daily_limit = self.config.requests_per_day

        minute_window = self.config.rate_limit_window_seconds
        daily_window = self.config.daily_window_seconds

        if minute_limit is not None and minute_limit <= 0:
            raise ValueError("requests_per_minute must be positive")

        if daily_limit is not None and daily_limit <= 0:
            raise ValueError("requests_per_day must be positive")

        if minute_window <= 0 or daily_window <= 0:
            raise ValueError("Quota windows must be positive")

        with self.rate_limit_lock:

            # Remove timestamps outside the rolling minute window.
            while (
                self.minute_timestamps
                and now - self.minute_timestamps[0] >= minute_window
            ):
                self.minute_timestamps.popleft()

            # Remove timestamps outside the rolling 24-hour window.
            while (
                self.daily_timestamps
                and now - self.daily_timestamps[0] >= daily_window
            ):
                self.daily_timestamps.popleft()

            retry_delays = []
            exceeded_limits = []

            if (
                minute_limit is not None
                and len(self.minute_timestamps) >= minute_limit
            ):
                retry_delays.append(
                    self.minute_timestamps[0] + minute_window - now
                )
                exceeded_limits.append("per-minute")

            if (
                daily_limit is not None
                and len(self.daily_timestamps) >= daily_limit
            ):
                retry_delays.append(
                    self.daily_timestamps[0] + daily_window - now
                )
                exceeded_limits.append("daily")

            # Do not reserve either quota if one or both are exhausted.
            if exceeded_limits:
                return {
                    "status": "rate_limited",
                    "answer": None,
                    "total_ms": 0,
                    "error": (
                        "Simulated quota exhausted: "
                        + ", ".join(exceeded_limits)
                    ),
                    "retry_after_seconds": round(
                        max(0, max(retry_delays)), 2
                    ),
                    "limit_type": ", ".join(exceeded_limits)
                }

            # Reserve the request in every enabled quota.
            if minute_limit is not None:
                self.minute_timestamps.append(now)

            if daily_limit is not None:
                self.daily_timestamps.append(now)

        return None

    def _register_waiting_request(self):
        with self.lock:
            self.waiting_requests += 1
            self.peak_queue_length = max(
                self.peak_queue_length,
                self.waiting_requests
            )

    def _acquire_request_slot(self):
        self.semaphore.acquire()

        with self.lock:
            self.waiting_requests -= 1
            self.active_requests += 1
            return self.active_requests

    def _release_request_slot(self):
        with self.lock:
            self.active_requests -= 1

        self.semaphore.release()

    def generate(self, prompt):
        """Generate a normal response with quota and failure simulation."""

        quota_result = self._check_request_quota()

        if quota_result:
            return quota_result

        if random.random() < self.config.rate_limit_rate:
            return {
                "status": "rate_limited",
                "answer": None,
                "total_ms": 0,
                "error": "Simulated random rate limit (HTTP 429)",
                "retry_after_seconds": 1,
                "limit_type": "random"
            }

        self._register_waiting_request()
        current_load = self._acquire_request_slot()

        start_time = time.perf_counter()

        try:
            if random.random() < self.config.failure_rate:
                return {
                    "status": "error",
                    "answer": None,
                    "total_ms": 0,
                    "error": "Simulated internal service error"
                }

            if random.random() < self.config.timeout_rate:
                time.sleep(self.config.base_latency * 2)

                return {
                    "status": "timeout",
                    "answer": None,
                    "total_ms": round(
                        (time.perf_counter() - start_time) * 1000, 2
                    ),
                    "error": "Simulated request timeout"
                }

            extra_latency = max(
                0,
                current_load - self.config.max_concurrent_requests
            ) * self.config.extra_load_latency

            time.sleep(self.config.base_latency + extra_latency)

            return {
                "status": "ok",
                "answer": f"Simulated answer for: {prompt[:100]}",
                "total_ms": round(
                    (time.perf_counter() - start_time) * 1000, 2
                ),
                "error": None
            }

        finally:
            self._release_request_slot()

    def generate_stream(self, prompt):
        """Stream a response while applying the same request quotas."""

        quota_result = self._check_request_quota()

        if quota_result:
            yield {
                "status": quota_result["status"],
                "piece": "",
                "error": quota_result["error"],
                "retry_after_seconds": quota_result[
                    "retry_after_seconds"
                ],
                "limit_type": quota_result["limit_type"]
            }
            return

        if random.random() < self.config.rate_limit_rate:
            yield {
                "status": "rate_limited",
                "piece": "",
                "error": "Simulated random rate limit (HTTP 429)",
                "retry_after_seconds": 1,
                "limit_type": "random"
            }
            return

        self._register_waiting_request()
        self._acquire_request_slot()

        start_time = time.perf_counter()
        first_token_ms = None

        answer = f"Simulated answer for: {prompt[:100]}"

        try:
            if random.random() < self.config.failure_rate:
                yield {
                    "status": "error",
                    "piece": "",
                    "error": "Simulated internal service error"
                }
                return

            if random.random() < self.config.timeout_rate:
                time.sleep(self.config.base_latency * 2)
                yield {
                    "status": "timeout",
                    "piece": "",
                    "error": "Simulated request timeout"
                }
                return

            for piece in answer.split():
                time.sleep(self.config.stream_piece_delay)

                if first_token_ms is None:
                    first_token_ms = (
                        time.perf_counter() - start_time
                    ) * 1000

                yield {
                    "status": "ok",
                    "piece": piece + " ",
                    "first_token_ms": round(first_token_ms, 2),
                    "elapsed_ms": round(
                        (time.perf_counter() - start_time) * 1000, 2
                    )
                }

        finally:
            self._release_request_slot()

    def get_metrics(self):
        with self.lock:
            metrics = {
                "active_requests": self.active_requests,
                "waiting_requests": self.waiting_requests,
                "peak_queue_length": self.peak_queue_length
            }

        with self.rate_limit_lock:
            metrics["requests_in_minute_window"] = len(
                self.minute_timestamps
            )
            metrics["requests_in_daily_window"] = len(
                self.daily_timestamps
            )

        return metrics
