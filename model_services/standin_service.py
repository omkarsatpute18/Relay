import random
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class StandinConfig:
    """Configuration for the controllable stand-in model service."""

    base_latency: float = 1.0
    extra_load_latency: float = 0.5
    max_concurrent_requests: int = 3

    failure_rate: float = 0.0
    timeout_rate: float = 0.0
    rate_limit_rate: float = 0.0
    refusal_rate: float = 0.0

    stream_piece_delay: float = 0.1

    requests_per_minute: Optional[int] = None
    requests_per_day: Optional[int] = None
    rate_limit_window_seconds: float = 60.0
    daily_window_seconds: float = 86400.0


class StandinService:
    """Simulates latency, concurrency, failures, quotas, refusals and streaming."""

    def __init__(self, config=None):
        self.config = config or StandinConfig()

        if self.config.max_concurrent_requests < 1:
            raise ValueError("max_concurrent_requests must be at least 1")

        for field in (
            "failure_rate",
            "timeout_rate",
            "rate_limit_rate",
            "refusal_rate",
        ):
            value = getattr(self.config, field)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field} must be between 0 and 1")

        if self.config.base_latency < 0:
            raise ValueError("base_latency cannot be negative")
        if self.config.extra_load_latency < 0:
            raise ValueError("extra_load_latency cannot be negative")
        if self.config.stream_piece_delay < 0:
            raise ValueError("stream_piece_delay cannot be negative")

        self.semaphore = threading.Semaphore(
            self.config.max_concurrent_requests
        )

        self.active_requests = 0
        self.waiting_requests = 0
        self.peak_queue_length = 0
        self.peak_in_flight = 0

        self.lock = threading.Lock()
        self.rate_limit_lock = threading.Lock()

        self.minute_timestamps = deque()
        self.daily_timestamps = deque()

    def _check_request_quota(self):
        """Atomically check and reserve enabled rolling-window quotas."""

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
            while (
                self.minute_timestamps
                and now - self.minute_timestamps[0] >= minute_window
            ):
                self.minute_timestamps.popleft()

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

            # A request is reserved only if all enabled quotas allow it.
            if exceeded_limits:
                return {
                    "status": "rate_limited",
                    "answer": None,
                    "total_ms": 0.0,
                    "error": (
                        "Simulated quota exhausted: "
                        + ", ".join(exceeded_limits)
                    ),
                    "retry_after_seconds": round(max(retry_delays), 2),
                    "limit_type": ", ".join(exceeded_limits),
                    "outcome": "service_limit",
                }

            if minute_limit is not None:
                self.minute_timestamps.append(now)
            if daily_limit is not None:
                self.daily_timestamps.append(now)

        return None

    def _register_waiting_request(self):
        """Register queue pressure before blocking on the semaphore."""

        with self.lock:
            self.waiting_requests += 1
            self.peak_queue_length = max(
                self.peak_queue_length, self.waiting_requests
            )

            # Include both active and waiting requests. This captures the
            # offered load that the semaphore alone would otherwise hide.
            requests_in_system = self.active_requests + self.waiting_requests
            overload_level = max(
                0,
                requests_in_system - self.config.max_concurrent_requests,
            )
            return overload_level

    def _acquire_request_slot(self):
        self.semaphore.acquire()
        with self.lock:
            self.waiting_requests -= 1
            self.active_requests += 1
            self.peak_in_flight = max(
                self.peak_in_flight, self.active_requests
            )
            return self.active_requests

    def _release_request_slot(self):
        with self.lock:
            self.active_requests -= 1
        self.semaphore.release()

    def _service_outcome(self):
        """Return a simulated service/model outcome."""
        draw = random.random()
        if draw < self.config.failure_rate:
            return "error"
        draw -= self.config.failure_rate
        if draw < self.config.timeout_rate:
            return "timeout"
        draw -= self.config.timeout_rate
        if draw < self.config.refusal_rate:
            return "refused"
        return "ok"

    def generate(self, prompt):
        """Generate a normal response and include end-to-end latency."""

        request_start = time.perf_counter()

        quota_result = self._check_request_quota()
        if quota_result:
            return quota_result

        if random.random() < self.config.rate_limit_rate:
            return {
                "status": "rate_limited",
                "answer": None,
                "total_ms": round(
                    (time.perf_counter() - request_start) * 1000, 2
                ),
                "error": "Simulated random rate limit (HTTP 429)",
                "retry_after_seconds": 1.0,
                "limit_type": "random",
                "outcome": "service_limit",
            }

        overload_level = self._register_waiting_request()
        try:
            self._acquire_request_slot()
        except BaseException:
            with self.lock:
                self.waiting_requests -= 1
            raise

        try:
            outcome = self._service_outcome()

            if outcome == "error":
                return {
                    "status": "error",
                    "answer": None,
                    "total_ms": round(
                        (time.perf_counter() - request_start) * 1000, 2
                    ),
                    "error": "Simulated internal service error",
                    "outcome": "service_error",
                }

            if outcome == "timeout":
                time.sleep(self.config.base_latency * 2)
                return {
                    "status": "timeout",
                    "answer": None,
                    "total_ms": round(
                        (time.perf_counter() - request_start) * 1000, 2
                    ),
                    "error": "Simulated request timeout",
                    "outcome": "service_timeout",
                }

            load_delay = overload_level * self.config.extra_load_latency
            time.sleep(self.config.base_latency + load_delay)

            if outcome == "refused":
                answer = (
                    "I cannot answer this request based on the available "
                    "information."
                )
                return {
                    "status": "ok",
                    "answer": answer,
                    "total_ms": round(
                        (time.perf_counter() - request_start) * 1000, 2
                    ),
                    "error": None,
                    "outcome": "refused",
                    "load_delay_ms": round(load_delay * 1000, 2),
                }

            return {
                "status": "ok",
                "answer": f"Simulated answer for: {prompt[:100]}",
                "total_ms": round(
                    (time.perf_counter() - request_start) * 1000, 2
                ),
                "error": None,
                "outcome": "answered",
                "load_delay_ms": round(load_delay * 1000, 2),
            }

        finally:
            self._release_request_slot()

    def generate_stream(self, prompt):
        """Yield response pieces; first-token timing includes queue waiting."""

        request_start = time.perf_counter()

        quota_result = self._check_request_quota()
        if quota_result:
            yield {
                "status": quota_result["status"],
                "piece": "",
                "error": quota_result["error"],
                "retry_after_seconds": quota_result["retry_after_seconds"],
                "limit_type": quota_result["limit_type"],
                "outcome": quota_result["outcome"],
            }
            return

        if random.random() < self.config.rate_limit_rate:
            yield {
                "status": "rate_limited",
                "piece": "",
                "error": "Simulated random rate limit (HTTP 429)",
                "retry_after_seconds": 1.0,
                "limit_type": "random",
                "outcome": "service_limit",
            }
            return

        overload_level = self._register_waiting_request()
        try:
            self._acquire_request_slot()
        except BaseException:
            with self.lock:
                self.waiting_requests -= 1
            raise

        try:
            outcome = self._service_outcome()

            if outcome == "error":
                yield {
                    "status": "error",
                    "piece": "",
                    "error": "Simulated internal service error",
                    "outcome": "service_error",
                }
                return

            if outcome == "timeout":
                time.sleep(self.config.base_latency * 2)
                yield {
                    "status": "timeout",
                    "piece": "",
                    "error": "Simulated request timeout",
                    "outcome": "service_timeout",
                }
                return

            load_delay = overload_level * self.config.extra_load_latency
            if load_delay:
                time.sleep(load_delay)

            if outcome == "refused":
                answer = (
                    "I cannot answer this request based on the available "
                    "information."
                )
                response_outcome = "refused"
            else:
                answer = f"Simulated answer for: {prompt[:100]}"
                response_outcome = "answered"

            first_token_ms = None
            for piece in answer.split():
                time.sleep(self.config.stream_piece_delay)
                elapsed_ms = (time.perf_counter() - request_start) * 1000

                if first_token_ms is None:
                    first_token_ms = elapsed_ms

                yield {
                    "status": "ok",
                    "piece": piece + " ",
                    "first_token_ms": round(first_token_ms, 2),
                    "elapsed_ms": round(elapsed_ms, 2),
                    "outcome": response_outcome,
                }

        finally:
            self._release_request_slot()

    def get_metrics(self):
        with self.lock:
            metrics = {
                "active_requests": self.active_requests,
                "waiting_requests": self.waiting_requests,
                "peak_queue_length": self.peak_queue_length,
                "peak_in_flight": self.peak_in_flight,
            }

        with self.rate_limit_lock:
            metrics["requests_in_minute_window"] = len(
                self.minute_timestamps
            )
            metrics["requests_in_daily_window"] = len(
                self.daily_timestamps
            )

        return metrics
