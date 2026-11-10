
from model_services.standin_service import StandinService, StandinConfig

print("\n===== STAND-IN SERVICE TEST =====")

# Test 1: Normal successful response
service = StandinService(
    StandinConfig(base_latency=0.1)
)

result = service.generate("Explain attention mechanism.")

print("\nTest 1 - Normal response")
print("Status:", result["status"])
print("Answer:", result["answer"])
print("Latency:", result["total_ms"], "ms")


# Test 2: Simulated model refusal
service = StandinService(
    StandinConfig(
        base_latency=0.1,
        refusal_rate=1.0
    )
)

result = service.generate("Answer an unsupported question.")

print("\nTest 2 - Model refusal")
print("Status:", result["status"])
print("Outcome:", result["outcome"])
print("Answer:", result["answer"])


# Test 3: Simulated internal failure
service = StandinService(
    StandinConfig(
        failure_rate=1.0
    )
)

result = service.generate("Test internal failure.")

print("\nTest 3 - Internal failure")
print("Status:", result["status"])
print("Error:", result["error"])


# Test 4: Per-minute quota exhaustion
service = StandinService(
    StandinConfig(
        base_latency=0,
        requests_per_minute=2,
        rate_limit_window_seconds=60
    )
)

print("\nTest 4 - Per-minute quota")

for i in range(3):
    result = service.generate(f"Quota request {i + 1}")
    print(f"Request {i + 1}:", result["status"])


# Test 5: Streaming response
service = StandinService(
    StandinConfig(
        stream_piece_delay=0.02
    )
)

print("\nTest 5 - Streaming response")

first_token = None
streamed_text = ""

for chunk in service.generate_stream("Test streaming response."):
    if chunk["status"] != "ok":
        print("Streaming failed:", chunk)
        break

    if first_token is None:
        first_token = chunk["first_token_ms"]

    streamed_text += chunk["piece"]

print("Streamed answer:", streamed_text)
print("First-token latency:", first_token, "ms")


# Test 6: Metrics
print("\nTest 6 - Service metrics")
print(service.get_metrics())

print("\n===== TESTS COMPLETED =====")
