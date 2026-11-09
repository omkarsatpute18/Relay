import re
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from groq import (
    Groq,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
)

load_dotenv()


class GroqService:

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("MODEL_NAME")

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing from .env")

        if not self.model:
            raise ValueError("MODEL_NAME is missing from .env")

        self.client = Groq(
            api_key=self.api_key,
            timeout=30.0,
            max_retries=0
        )

        print("Groq service initialized.")
        print("Selected model:", self.model)

    
    @staticmethod
    def _extract_retry_information(error):

        response = getattr(error, "response", None)
        headers = getattr(response, "headers", {}) or {}

        # Preserve provider rate-limit and retry headers.
        useful_headers = {
            str(key): str(value)
            for key, value in headers.items()
            if (
                "ratelimit" in str(key).lower()
                or "retry-after" in str(key).lower()
            )
        }

        retry_after = None

        # First preference: explicit Retry-After header.
        header_value = headers.get("retry-after")

        if header_value:
            try:
                retry_after = float(header_value)
            except (TypeError, ValueError):
                pass

        error_text = str(error)

        # Second preference: recovery duration in the error message.
        if retry_after is None:
            match = re.search(
                r"try again in\s+([\d.]+)\s*s",
                error_text,
                re.IGNORECASE
            )

            if match:
                retry_after = float(match.group(1))

        # Third preference: token-window reset header.
        if retry_after is None:
            reset_value = None

            for key, value in useful_headers.items():
                if key.lower() == "x-ratelimit-reset-tokens":
                    reset_value = value
                    break

            if reset_value:
                match = re.fullmatch(
                    r"(?:(\d+(?:\.\d+)?)m)?"
                    r"(?:(\d+(?:\.\d+)?)s)?",
                    reset_value.strip()
                )

                if match:
                    minutes = float(match.group(1) or 0)
                    seconds = float(match.group(2) or 0)
                    retry_after = minutes * 60 + seconds

        return retry_after, useful_headers


    @staticmethod
    def _timestamp():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _headers(response):
        if response is None:
            return {}

        headers = getattr(response, "headers", None)

        if not headers:
            return {}

        # Preserve rate-limit headers for later analysis.
        return {
            str(key): str(value)
            for key, value in headers.items()
            if "ratelimit" in str(key).lower()
            or "retry-after" in str(key).lower()
        }

    def generate(self, messages, max_tokens=800):

        start_time = time.perf_counter()
        start_timestamp = self._timestamp()

        try:

            raw_response = (
                self.client.chat.completions
                .with_raw_response.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_completion_tokens=max_tokens,
                    stream=False
                )
            )

            response = raw_response.parse()

            total_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            return {
                "status": "ok",
                "answer": response.choices[0].message.content,
                "model": self.model,
                "start_time": start_timestamp,
                "first_token_ms": None,
                "total_ms": total_ms,
                "tokens_in": response.usage.prompt_tokens,
                "tokens_out": response.usage.completion_tokens,
                "finish_reason": response.choices[0].finish_reason,
                "http_status": 200,
                "rate_limit_headers": self._headers(raw_response),
                "retries": 0,
                "error": None
            }

        except RateLimitError as error:
            return self._error_result(
                "rate_limited", error, start_time, start_timestamp
            )

        except APITimeoutError as error:
            return self._error_result(
                "timeout", error, start_time, start_timestamp
            )

        except APIConnectionError as error:
            return self._error_result(
                "error", error, start_time, start_timestamp
            )

        except APIStatusError as error:
            return self._error_result(
                "error", error, start_time, start_timestamp
            )

        except Exception as error:
            return self._error_result(
                "error", error, start_time, start_timestamp
            )

    def generate_stream(self, messages, max_tokens=800):

        start_time = time.perf_counter()
        start_timestamp = self._timestamp()
        first_token_ms = None
        full_answer = ""
        rate_limit_headers = {}

        try:

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_completion_tokens=max_tokens,
                stream=True
            )

            for chunk in stream:

                if not chunk.choices:
                    continue

                content = chunk.choices[0].delta.content

                if content:

                    if first_token_ms is None:
                        first_token_ms = round(
                            (time.perf_counter() - start_time) * 1000,
                            2
                        )

                    full_answer += content
                    print(content, end="", flush=True)

            total_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2
            )

            return {
                "status": "ok",
                "answer": full_answer,
                "model": self.model,
                "start_time": start_timestamp,
                "first_token_ms": first_token_ms,
                "total_ms": total_ms,
                "tokens_in": None,
                "tokens_out": None,
                "finish_reason": None,
                "http_status": 200,
                "rate_limit_headers": rate_limit_headers,
                "retries": 0,
                "error": None
            }

        except RateLimitError as error:
            return self._error_result(
                "rate_limited", error, start_time, start_timestamp
            )

        except APITimeoutError as error:
            return self._error_result(
                "timeout", error, start_time, start_timestamp
            )

        except APIConnectionError as error:
            return self._error_result(
                "error", error, start_time, start_timestamp
            )

        except APIStatusError as error:
            return self._error_result(
                "error", error, start_time, start_timestamp
            )

        except Exception as error:
            return self._error_result(
                "error", error, start_time, start_timestamp
            )

    
    @staticmethod
    def _error_result(
        status, error, start_time, start_timestamp
    ):

        elapsed_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        http_status = getattr(error, "status_code", None)

        retry_after, rate_limit_headers = (
            GroqService._extract_retry_information(error)
        )

        return {
            "status": status,
            "answer": None,
            "model": None,
            "start_time": start_timestamp,
            "first_token_ms": None,
            "total_ms": elapsed_ms,
            "tokens_in": None,
            "tokens_out": None,
            "finish_reason": None,
            "http_status": http_status,
            "rate_limit_headers": rate_limit_headers,
            "retry_after_seconds": retry_after,
            "retries": 0,
            "error": str(error)
        }



if __name__ == "__main__":

    service = GroqService()

    messages = [
        {
            "role": "system",
            "content": "Answer accurately and concisely."
        },
        {
            "role": "user",
            "content": "Explain multi-head attention briefly."
        }
    ]

    print("\nTesting normal generation...")

    result = service.generate(messages)

    for key, value in result.items():
        if key != "error":
            print(f"{key}: {value}")

    if result["error"]:
        print("Error:", result["error"])

    print("\nTesting streaming generation...")

    stream_result = service.generate_stream(messages)

    print("\n")

    for key, value in stream_result.items():
        if key != "error":
            print(f"{key}: {value}")

    if stream_result["error"]:
        print("Streaming error:", stream_result["error"])
