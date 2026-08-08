"""
Baseline benchmark for AJU RAG backend.
Calls POST /api/v1/query 5 times per scenario and reports per-phase latencies.
Requires: uvicorn running at http://127.0.0.1:8000
"""
import asyncio
import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"
RUNS = 5

SCENARIOS = [
    {"name": "Public – admission query",      "query": "What are the admission requirements?", "persona": "public"},
    {"name": "Student – course registration", "query": "How do I register for courses this semester?", "persona": "student"},
    {"name": "Staff – budget information",    "query": "What is the current university budget allocation?", "persona": "staff"},
    {"name": "No-result – irrelevant query",  "query": "How do I repair a Mars rover?", "persona": "public"},
]


def post_json(url: str, payload: dict) -> tuple[dict, float]:
    """POST JSON and return (response_dict, elapsed_ms)."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        data = {"error": str(e)}
    elapsed = (time.perf_counter() - t0) * 1000
    return data, elapsed


def run_benchmark():
    print("=" * 60)
    print("  AJU RAG BACKEND — BASELINE BENCHMARK")
    print("=" * 60)

    all_results = []

    for scenario in SCENARIOS:
        latencies = []
        print(f"\n[{scenario['name']}]")
        for i in range(RUNS):
            resp, ms = post_json(
                f"{BASE_URL}/api/v1/query",
                {"query": scenario["query"], "persona": scenario["persona"]},
            )
            latencies.append(ms)
            conf = resp.get("confidence_score", "n/a")
            srcs = len(resp.get("sources", []))
            print(f"  Run {i+1}: {ms:7.1f} ms | confidence={conf} | sources={srcs}")

        avg = sum(latencies) / len(latencies)
        mn  = min(latencies)
        mx  = max(latencies)
        print(f"  AVG: {avg:.1f} ms  MIN: {mn:.1f} ms  MAX: {mx:.1f} ms")
        all_results.append({"scenario": scenario["name"], "avg_ms": avg, "min_ms": mn, "max_ms": mx})

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  {'Scenario':<40} {'Avg(ms)':>8}  {'Min(ms)':>8}  {'Max(ms)':>8}")
    print("  " + "-" * 68)
    for r in all_results:
        print(f"  {r['scenario']:<40} {r['avg_ms']:>8.1f}  {r['min_ms']:>8.1f}  {r['max_ms']:>8.1f}")
    print("=" * 60)

    # Save results to JSON for later comparison
    output = {
        "phase": "baseline",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runs_per_scenario": RUNS,
        "results": all_results,
    }
    with open("scripts/benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to scripts/benchmark_results.json")


if __name__ == "__main__":
    run_benchmark()
