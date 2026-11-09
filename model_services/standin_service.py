
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

    # Request quota settings.
    # None disables the per-minute quota.
    requests_per_minute: Optional[int] = None
    rate_limit_window_seconds: float = 60.0


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

        # Stores arrival timestamps for the sliding-window limiter.
        self.request_timestamps = deque()
        self.rate_limit_lock = threading.Lock()

    def _check_request_quota(self):
        """Check and reserve a request against the configured quota."""

        limit = self.config.requests_per_minute

        if limit is None:
            return None

        if limit <= 0:
            raise ValueError("requests_per_minute must be greater than zero")

        now = time.monotonic()
        window = self.config.rate_limit_window_seconds

        with self.rate_limit_lock:

            # Remove requests outside the current time window.
            while (
                self.request_timestamps
                and now - self.request_timestamps[0] >= window
            ):
                self.request_timestamps.popleft()

            # Reject requests when the quota is exhausted.
            if len(self.request_timestamps) >= limit:
                retry_after = (
                    self.request_timestamps[0] + window - now
                )

                return {
                    "status": "rate_limited",
                    "answer": None,
                    "total_ms": 0,
                    "error": "Simulated per-minute request limit exceeded",
                    "retry_after_seconds": round(
                        max(0, retry_after), 2
                    )
                }

            # Reserve a position in the request quota.
            self.request_timestamps.append(now)

        return None

    def generate(self, prompt):

        # Apply the request quota before acquiring a concurrency slot.
        quota_result = self._check_request_quota()

        if quota_result:
            return quota_result

        # Preserve the original random rate-limit simulation.
        if random.random() < self.config.rate_limit_rate:
            return {
                "status": "rate_limited",
                "answer": None,
                "total_ms": 0,
                "error": "Simulated random rate limit (HTTP 429)",
                "retry_after_seconds": 1
            }

        # Register the request as waiting.
        with self.lock:
            self.waiting_requests += 1
            self.peak_queue_length = max(
                self.peak_queue_length,
                self.waiting_requests
            )

        self.semaphore.acquire()

        with self.lock:
            self.waiting_requests -= 1
            self.active_requests += 1
            current_load = self.active_requests

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
            with self.lock:
                self.active_requests -= 1

            self.semaphore.release()

    def generate_stream(self, prompt):
        """Stream a response while tracking queue and latency."""

        answer = f"Simulated answer for: {prompt[:100]}"
        first_token_ms = None
        start_time = time.perf_counter()

        # Register the request in the waiting queue.
        with self.lock:
            self.waiting_requests += 1
            self.peak_queue_length = max(
                self.peak_queue_length,
                self.waiting_requests
            )

        self.semaphore.acquire()

        with self.lock:
            self.waiting_requests -= 1
            self.active_requests += 1

        try:
            for piece in answer.split():
                time.sleep(self.config.stream_piece_delay)

                if first_token_ms is None:
                    first_token_ms = (
                        time.perf_counter() - start_time
                    ) * 1000

                yield {
                    "piece": piece + " ",
                    "first_token_ms": round(first_token_ms, 2),
                    "elapsed_ms": round(
                        (time.perf_counter() - start_time) * 1000, 2
                    )
                }

        finally:
            with self.lock:
                self.active_requests -= 1

            self.semaphore.release()

    def get_metrics(self):
        with self.lock:
            metrics = {
                "active_requests": self.active_requests,
                "waiting_requests": self.waiting_requests,
                "peak_queue_length": self.peak_queue_length
            }

        with self.rate_limit_lock:
            metrics["requests_in_current_window"] = len(
                self.request_timestamps
            )

        return metrics
