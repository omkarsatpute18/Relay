
import time
from model_services.standin_service import StandinService

service = StandinService()

start_time = time.perf_counter()
first_token_ms = None

print("Streaming response:")

for chunk in service.generate_stream("Explain attention"):
    if first_token_ms is None:
        first_token_ms = chunk["first_token_ms"]

    print(chunk["piece"], end="", flush=True)

total_ms = (time.perf_counter() - start_time) * 1000

print("\n\nStreaming measurements:")
print("First token latency:", first_token_ms, "ms")
print("Total streaming time:", round(total_ms, 2), "ms")
