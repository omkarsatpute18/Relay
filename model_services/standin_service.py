
import time
import random
import threading
from dataclasses import dataclass


@dataclass
class StandinConfig:
    base_latency: float = 1.0
    extra_load_latency: float = 0.5
    max_concurrent_requests: int = 3
    failure_rate: float = 0.0
    timeout_rate: float = 0.0
    rate_limit_rate: float = 0.0
    stream_piece_delay: float = 0.1


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

    def generate(self, prompt):
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
            if random.random() < self.config.rate_limit_rate:
                return {
                    "status": "rate_limited",
                    "answer": None,
                    "total_ms": 0,
                    "error": "Simulated rate limit (HTTP 429)"
                }

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
            return {
                "active_requests": self.active_requests,
                "waiting_requests": self.waiting_requests,
                "peak_queue_length": self.peak_queue_length
            }
