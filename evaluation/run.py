"""
Run evaluation cases against the pipeline and save a JSON report.

Usage:
    python -m evaluation.run --list
    python -m evaluation.run --case simple-factual
    python -m evaluation.run                    # runs all cases
    python -m evaluation.run --depth quick      # override depth for all cases

Optional env:
    DB_PATH=researchbot-eval.db                 # use a separate database
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from request import ResearchRequest
from evaluation.cases import CASES
import research
from core import database


RESULTS_DIR = Path("evaluation") / "results"


def _summary_from_db(research_id):
    """Pull a small deterministic summary of what the pipeline produced."""
    try:
        job = database.get_research(research_id)
        sources = database.get_sources_for_research(research_id, only_verified=True)
        claims = database.get_claims(research_id)
        rels = database.get_relationships(research_id)
        answer = database.get_answer(research_id)
    except Exception as e:
        return {"error": f"db_read_failed: {e}"}

    avg_conf = None
    if claims:
        vals = [c["confidence_score"] for c in claims if c["confidence_score"] is not None]
        if vals:
            avg_conf = round(sum(vals) / len(vals), 1)

    return {
        "verified_source_count": len(sources),
        "claim_count": len(claims),
        "relationship_count": len(rels),
        "average_claim_confidence": avg_conf,
        "answer_verification_status": answer["verification_status"] if answer else None,
        "answer_length_chars": len(answer["content"]) if answer else 0,
    }


def _run_case(case, depth_override=None):
    depth = depth_override or case.get("depth", "standard")
    topic = case["question"]

    print(f"\n=== [{case['id']}] ({depth}) {topic} ===")

    request = ResearchRequest(topic=topic, depth=depth)
    start = time.time()

    def progress_callback(rid, stage):
        print(f"  [{rid}] {stage}")

    research_id = research.research(
        request,
        user_telegram_id="eval_user",
        progress_callback=progress_callback,
    )

    # Wait for completion
    while True:
        job = database.get_research(research_id)
        if job and job["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(1)

    duration = round(time.time() - start, 1)
    result = {
        "case_id": case["id"],
        "category": case["category"],
        "depth": depth,
        "question": topic,
        "research_id": research_id,
        "final_status": job["status"],
        "error": job["error"],
        "duration_seconds": duration,
        "summary": _summary_from_db(research_id),
    }

    print(f"  -> {result['final_status']} in {duration}s "
          f"({result['summary'].get('verified_source_count', 0)} sources, "
          f"{result['summary'].get('claim_count', 0)} claims)")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="List case ids and exit")
    parser.add_argument("--case", help="Run only this case id")
    parser.add_argument("--depth", choices=["quick", "standard", "deep", "exhaustive"],
                        help="Override the depth for every case")
    args = parser.parse_args()

    if args.list:
        for c in CASES:
            print(f"{c['id']:22s} [{c['depth']:10s}] {c['question']}")
        return

    database.init_db()

    selected = CASES
    if args.case:
        selected = [c for c in CASES if c["id"] == args.case]
        if not selected:
            print(f"No case with id '{args.case}'.")
            return

    results = []
    for case in selected:
        results.append(_run_case(case, depth_override=args.depth))

    # Write report
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report_path = RESULTS_DIR / f"{stamp}.json"
    report = {
        "timestamp": stamp,
        "db_path": os.getenv("DB_PATH", "researchbot.db"),
        "case_count": len(results),
        "results": results,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()