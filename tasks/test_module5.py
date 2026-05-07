import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from modules.lit_monitor import search_pubmed, score_relevance, generate_digest, send_discord_digest, LitResult, LitDigest

# Test 1: search_pubmed (real network call, low max_results)
results = search_pubmed("cefiderocol", days_back=365, max_results=5)
print(f"search_pubmed: found {len(results)} results")
assert isinstance(results, list)
if results:
    assert all(isinstance(r, LitResult) for r in results)
    assert all(r.pmid for r in results)
    print(f"  First result: {results[0].title[:60]}...")

# Test 2: score_relevance
if results:
    scored = score_relevance(results, "cefiderocol")
    assert all(0.0 <= r.relevance_score <= 1.0 for r in scored)
    print(f"score_relevance: top score = {scored[0].relevance_score:.3f}")

# Test 3: generate_digest (LLM)
if results:
    digest = generate_digest("cefiderocol", scored[:3])
    assert isinstance(digest, LitDigest)
    assert digest.drug_name == "cefiderocol"
    assert digest.search_date
    print(f"generate_digest: digest_text length = {len(digest.digest_text)} chars")
    print(f"  Escalations: {len(digest.escalations)}")

# Test 4: send_discord_digest
if results:
    # This will use the token from .env or environment
    ok = send_discord_digest(digest, channel_name="lit-monitor")
    if ok:
        print("send_discord_digest: delivered to #lit-monitor")
    else:
        print("send_discord_digest: failed (likely no token or channel not found)")

print("\nAll tests passed.")
