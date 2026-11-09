
import os
import time

from dotenv import load_dotenv
from groq import (
    Groq,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
)


# Load project environment variables
load_dotenv()


class GroqService:

    def __init__(self):

        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("MODEL_NAME")

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY is missing from .env"
            )

        if not self.model:
            raise ValueError(
                "MODEL_NAME is missing from .env"
            )

        self.client = Groq(
            api_key=self.api_key,
            timeout=30.0,
            max_retries=0
        )

        print("Groq service initialized.")
        print("Selected model:", self.model)

    def generate(self, messages, max_tokens=500):

        start_time = time.perf_counter()

        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_completion_tokens=max_tokens,
                stream=False
            )

            end_time = time.perf_counter()

            answer = response.choices[0].message.content

            return {
                "status": "ok",
                "answer": answer,
                "model": self.model,
                "first_token_ms": None,
                "total_ms": round(
                    (end_time - start_time) * 1000, 2
                ),
                "tokens_in": response.usage.prompt_tokens,
                "tokens_out": response.usage.completion_tokens,
                "error": None
            }

        except RateLimitError as error:

            return self._error_result(
                "rate_limited", error
            )

        except APITimeoutError as error:

            return self._error_result(
                "timeout", error
            )

        except APIConnectionError as error:

            return self._error_result(
                "error", error
            )

        except APIStatusError as error:

            return self._error_result(
                "error", error
            )

    def generate_stream(self, messages, max_tokens=500):

        start_time = time.perf_counter()
        first_token_ms = None
        full_answer = ""

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
                            (time.perf_counter() - start_time)
                            * 1000,
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
                "first_token_ms": first_token_ms,
                "total_ms": total_ms,
                "tokens_in": None,
                "tokens_out": None,
                "error": None
            }

        except RateLimitError as error:

            return self._error_result(
                "rate_limited", error
            )

        except APITimeoutError as error:

            return self._error_result(
                "timeout", error
            )

        except APIConnectionError as error:

            return self._error_result(
                "error", error
            )

        except APIStatusError as error:

            return self._error_result(
                "error", error
            )

    @staticmethod
    def _error_result(status, error):

        return {
            "status": status,
            "answer": None,
            "model": None,
            "first_token_ms": None,
            "total_ms": None,
            "tokens_in": None,
            "tokens_out": None,
            "error": str(error)
        }


if __name__ == "__main__":

    service = GroqService()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful research assistant. "
                "Answer accurately and concisely."
            )
        },
        {
            "role": "user",
            "content": (
                "Explain multi-head attention in simple terms."
            )
        }
    ]

    print("\nTesting normal generation...")

    result = service.generate(messages)

    print("\nStatus:", result["status"])
    print("Answer:", result["answer"])
    print("Model:", result["model"])
    print("Total time:", result["total_ms"], "ms")
    print("Input tokens:", result["tokens_in"])
    print("Output tokens:", result["tokens_out"])

    if result["error"]:
        print("\nERROR DETAILS:")
        print(result["error"])
    print("\nTesting streaming generation...")

    stream_result = service.generate_stream(messages)

    print("\n\nStreaming status:", stream_result["status"])
    print(
        "Time to first token:",
        stream_result["first_token_ms"],
        "ms"
    )
    print(
        "Total streaming time:",
        stream_result["total_ms"],
        "ms"
    )

    if stream_result["error"]:
        print("\nSTREAMING ERROR:")
        print(stream_result["error"])