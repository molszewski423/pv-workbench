"""
Phase 1 Retrieval Benchmark

Evaluates vault ingestion quality against 30 gold-standard PV questions.
Metrics: precision@5 (source note in top 5 chunks) and MRR.

Usage (from pv-workbench/ root):
    PYTHONPATH=src python tests/benchmark/run_benchmark.py
    PYTHONPATH=src python tests/benchmark/run_benchmark.py --output results/run_001.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ingester.vault_ingester import query_vault
from config import TOP_K


def reciprocal_rank(hits: list[dict], expected_notes: list[str]) -> float:
    """
    Return 1/rank of first hit matching any expected source note, or 0.
    Supports multiple acceptable sources per question.
    """
    for i, h in enumerate(hits, 1):
        src = h["source_note"].lower()
        if any(note.lower() in src for note in expected_notes):
            return 1.0 / i
    return 0.0


def _get_expected_notes(q: dict) -> list[str]:
    """Return list of acceptable source notes for a question (backward compatible)."""
    if "source_notes" in q:
        return q["source_notes"]
    return [q["source_note"]]


def run_benchmark(questions: list[dict], n_results: int = TOP_K) -> dict:
    results = []
    hits_at_5 = 0

    for q in questions:
        hits = query_vault(q["question"], n_results=n_results)
        expected = _get_expected_notes(q)
        rr = reciprocal_rank(hits, expected)
        found_in_top5 = rr > 0

        if found_in_top5:
            hits_at_5 += 1

        results.append({
            "id": q["id"],
            "module": q["module"],
            "question": q["question"],
            "expected_notes": expected,
            "found_in_top5": found_in_top5,
            "reciprocal_rank": rr,
            "top_hit": hits[0]["source_note"] if hits else "",
            "top_distance": hits[0]["distance"] if hits else None,
        })

        status = "✓" if found_in_top5 else "✗"
        print(f"  [{status}] {q['id']}: {q['question'][:60]}...")
        if not found_in_top5 and hits:
            print(f"       Got: {hits[0]['source_note']} (dist={hits[0]['distance']})")

    n = len(questions)
    precision_at_5 = hits_at_5 / n
    mrr = sum(r["reciprocal_rank"] for r in results) / n

    summary = {
        "run_timestamp": datetime.now().isoformat(),
        "n_questions": n,
        "precision_at_5": round(precision_at_5, 3),
        "mrr": round(mrr, 3),
        "hits_at_5": hits_at_5,
        "by_module": {},
        "results": results,
    }

    # Per-module breakdown
    modules = set(q["module"] for q in questions)
    for mod in modules:
        mod_results = [r for r in results if r["module"] == mod]
        mod_hits = sum(1 for r in mod_results if r["found_in_top5"])
        summary["by_module"][mod] = {
            "n": len(mod_results),
            "hits": mod_hits,
            "precision_at_5": round(mod_hits / len(mod_results), 3),
            "mrr": round(sum(r["reciprocal_rank"] for r in mod_results) / len(mod_results), 3),
        }

    return summary


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Precision@5:  {summary['precision_at_5']:.1%}  ({summary['hits_at_5']}/{summary['n_questions']})")
    print(f"MRR:          {summary['mrr']:.3f}")
    print("\nBy module:")
    for mod, stats in sorted(summary["by_module"].items()):
        print(f"  {mod:<25} P@5={stats['precision_at_5']:.1%}  MRR={stats['mrr']:.3f}  ({stats['hits']}/{stats['n']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", type=str, help="Save results JSON to this path")
    parser.add_argument("--n", type=int, default=TOP_K, help="Chunks to retrieve per question")
    args = parser.parse_args()

    benchmark_path = Path(__file__).parent / "gold_standard_qa.json"
    with open(benchmark_path) as f:
        data = json.load(f)

    questions = data["questions"]
    print(f"Running {len(questions)}-question benchmark (top-{args.n} retrieval)...\n")

    summary = run_benchmark(questions, n_results=args.n)
    print_summary(summary)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved: {out_path}")
