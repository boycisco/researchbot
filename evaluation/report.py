"""
Read evaluation reports and print metrics.

Usage:
    python -m evaluation.report                       # newest report
    python -m evaluation.report --file <path>         # specific report
    python -m evaluation.report --compare <path>      # newest vs. given
    python -m evaluation.report --list                # list available reports
"""

import argparse
import json
from pathlib import Path

from evaluation.metrics import report_metrics, compare_reports


RESULTS_DIR = Path("evaluation") / "results"


def _load(path):
    return json.loads(Path(path).read_text())


def _newest_report_path():
    if not RESULTS_DIR.exists():
        return None
    files = sorted(RESULTS_DIR.glob("*.json"))
    return files[-1] if files else None


def _fmt(v, suffix=""):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v}{suffix}"
    return f"{v}{suffix}"


def print_report(report, path):
    metrics = report_metrics(report)
    totals = metrics["totals"]

    print(f"\nReport: {path}")
    print(f"Timestamp: {report.get('timestamp', '?')}")
    print(f"Database: {report.get('db_path', '?')}")
    print()

    print("TOTALS")
    print(f"  Cases               : {totals['case_count']}")
    print(f"  Completed           : {totals['completed_count']} "
          f"(pass rate {_fmt(totals['pass_rate'])})")
    print(f"  Fact check pass rate: {_fmt(totals['fact_check_pass_rate'])} "
          f"over {totals['fact_checked_count']} answered case(s)")
    print(f"  Mean duration       : {_fmt(totals['mean_duration_seconds'], 's')}")
    print(f"  Mean confidence     : {_fmt(totals['mean_confidence'])}")
    print(f"  Mean source count   : {_fmt(totals['mean_source_count'])}")
    print(f"  Mean claim count    : {_fmt(totals['mean_claim_count'])}")
    print(f"  Total sources       : {totals['total_sources']}")
    print(f"  Total claims        : {totals['total_claims']}")

    print("\nBY STATUS")
    for status, count in metrics["by_status"].items():
        print(f"  {status:20s} {count}")

    print("\nBY CATEGORY")
    for cat, bucket in metrics["by_category"].items():
        print(f"  {cat:22s} {bucket['completed']}/{bucket['total']} completed "
              f"(mean {_fmt(bucket['mean_duration'], 's')})")

    print("\nPER CASE")
    for m in metrics["per_case"]:
        status = "OK " if m["completed"] else "FAIL"
        fc = "—" if m["fact_check_passed"] is None else (
            "PASS" if m["fact_check_passed"] else "FAIL"
        )
        print(f"  [{status}] {m['case_id']:22s} "
              f"{m['duration_seconds']:6.1f}s  "
              f"sources={m['verified_source_count']:2d}  "
              f"claims={m['claim_count']:2d}  "
              f"conf={_fmt(m['average_confidence'])}  "
              f"fact={fc}")


def print_comparison(old_report, old_path, new_report, new_path):
    diff = compare_reports(old_report, new_report)
    print(f"\nComparison: {old_path}  ->  {new_path}\n")
    for k, v in diff.items():
        old = v["old"]
        new = v["new"]
        delta = v["delta"]
        delta_str = "—" if delta is None else (f"{delta:+.3f}" if delta else "0")
        print(f"  {k:28s} {str(old):>10s}  ->  {str(new):>10s}   ({delta_str})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Path to a specific report")
    parser.add_argument("--compare", help="Compare newest report against this one")
    parser.add_argument("--list", action="store_true", help="List available reports")
    args = parser.parse_args()

    if args.list:
        if not RESULTS_DIR.exists():
            print("No results directory.")
            return
        for f in sorted(RESULTS_DIR.glob("*.json")):
            print(f.name)
        return

    if args.compare:
        old_path = Path(args.compare)
        new_path = Path(args.file) if args.file else _newest_report_path()
        if not old_path.exists() or not new_path or not new_path.exists():
            print("One of the reports does not exist.")
            return
        print_comparison(_load(old_path), str(old_path), _load(new_path), str(new_path))
        return

    path = Path(args.file) if args.file else _newest_report_path()
    if not path or not path.exists():
        print("No report found. Run `python -m evaluation.run --case <id>` first.")
        return
    print_report(_load(path), str(path))


if __name__ == "__main__":
    main()