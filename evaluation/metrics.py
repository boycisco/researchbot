"""
Pure functions that turn an evaluation report into metrics.

A "report" is the JSON written by evaluation/run.py:
    { "timestamp": ..., "results": [ {case result}, ... ] }

A "case result" has at minimum:
    case_id, category, depth, final_status, duration_seconds,
    summary: { verified_source_count, claim_count, average_claim_confidence,
               answer_verification_status, answer_length_chars, ... }
"""


def _safe_div(numerator, denominator, default=0.0):
    if not denominator:
        return default
    return numerator / denominator


def case_metrics(case_result):
    """Compute per-case metrics from a single case result dict."""
    summary = case_result.get("summary") or {}

    duration = case_result.get("duration_seconds") or 0
    source_count = summary.get("verified_source_count") or 0
    claim_count = summary.get("claim_count") or 0
    relationship_count = summary.get("relationship_count") or 0
    avg_conf = summary.get("average_claim_confidence")
    answer_chars = summary.get("answer_length_chars") or 0
    verification = summary.get("answer_verification_status")

    return {
        "case_id": case_result.get("case_id"),
        "category": case_result.get("category"),
        "depth": case_result.get("depth"),

        # 1 = completed, 0 = anything else
        "completed": 1 if case_result.get("final_status") == "completed" else 0,

        # 1 = answer passed fact check, 0 = not, None = no answer
        "fact_check_passed": (
            1 if verification == "verified" else
            0 if verification is not None else
            None
        ),

        "duration_seconds": duration,
        "verified_source_count": source_count,
        "claim_count": claim_count,
        "relationship_count": relationship_count,
        "average_confidence": avg_conf,
        "answer_length_chars": answer_chars,

        # Derived
        "claims_per_source": round(_safe_div(claim_count, source_count), 2),
        "relationships_per_claim": round(_safe_div(relationship_count, max(1, claim_count)), 2),
        "seconds_per_claim": round(_safe_div(duration, max(1, claim_count)), 1),
    }


def report_metrics(report):
    """
    Compute aggregate metrics across all cases in a report.

    Returns a dict with:
      - per_case:  [case_metrics(c), ...]
      - totals:    counts and means across cases
      - by_status: {status: count}
      - by_category: {category: {completed, total, mean_duration}}
    """
    results = report.get("results", [])
    per_case = [case_metrics(r) for r in results]

    total = len(per_case)
    completed = sum(1 for m in per_case if m["completed"] == 1)
    fact_checked = [m for m in per_case if m["fact_check_passed"] is not None]
    fact_passed = sum(1 for m in fact_checked if m["fact_check_passed"] == 1)

    durations = [m["duration_seconds"] for m in per_case if m["completed"] == 1]
    confidences = [m["average_confidence"] for m in per_case if m["average_confidence"] is not None]
    sources = [m["verified_source_count"] for m in per_case]
    claims = [m["claim_count"] for m in per_case]

    by_status = {}
    for r in results:
        s = r.get("final_status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1

    by_category = {}
    for m in per_case:
        cat = m["category"] or "unknown"
        bucket = by_category.setdefault(cat, {"total": 0, "completed": 0, "durations": []})
        bucket["total"] += 1
        bucket["completed"] += m["completed"]
        if m["completed"]:
            bucket["durations"].append(m["duration_seconds"])

    # Simplify the durations list into a mean
    for cat, bucket in by_category.items():
        ds = bucket.pop("durations")
        bucket["mean_duration"] = round(sum(ds) / len(ds), 1) if ds else None

    totals = {
        "case_count": total,
        "completed_count": completed,
        "pass_rate": round(_safe_div(completed, total), 3),
        "fact_checked_count": len(fact_checked),
        "fact_check_pass_rate": (
            round(_safe_div(fact_passed, len(fact_checked)), 3)
            if fact_checked else None
        ),
        "mean_duration_seconds": round(sum(durations) / len(durations), 1) if durations else None,
        "mean_confidence": round(sum(confidences) / len(confidences), 1) if confidences else None,
        "mean_source_count": round(sum(sources) / len(sources), 1) if sources else None,
        "mean_claim_count": round(sum(claims) / len(claims), 1) if claims else None,
        "total_claims": sum(claims),
        "total_sources": sum(sources),
    }

    return {
        "per_case": per_case,
        "totals": totals,
        "by_status": by_status,
        "by_category": by_category,
    }


def compare_reports(old_report, new_report):
    """
    Return a diff dict showing how key metrics changed between two reports.
    Only metrics present in both reports are compared.
    """
    a = report_metrics(old_report)["totals"]
    b = report_metrics(new_report)["totals"]

    keys = [
        "pass_rate",
        "fact_check_pass_rate",
        "mean_duration_seconds",
        "mean_confidence",
        "mean_source_count",
        "mean_claim_count",
    ]

    diff = {}
    for k in keys:
        va = a.get(k)
        vb = b.get(k)
        if va is None or vb is None:
            diff[k] = {"old": va, "new": vb, "delta": None}
        else:
            diff[k] = {"old": va, "new": vb, "delta": round(vb - va, 3)}
    return diff