"""
Lightweight health checks for the research bot.

Usage:
    python -m health                 # run non-AI checks
    python -m health --with-ai       # also test the AI provider (uses quota)

Each check returns (ok: bool, message: str). The module prints a summary
and exits with code 0 if all checks pass, 1 otherwise.

Nothing here performs a full research run. These checks are intentionally
cheap so you can run them on startup or in a monitoring loop.
"""

import argparse
import sys
import time
import traceback

import config
import utils
from core import database
from core import providers

logger = utils.logger


# --- Individual checks -------------------------------------------------

def check_database():
    try:
        database.init_db()
        conn = database.get_connection()
        row = conn.execute("SELECT 1 AS ok").fetchone()
        conn.close()
        if row and row["ok"] == 1:
            return True, "database is reachable and schema is initialized"
        return False, "database returned unexpected result"
    except Exception as e:
        return False, f"database check failed: {e}"


def check_ai():
    """One tiny AI call. Consumes quota. Only run when explicitly asked."""
    try:
        start = time.time()
        result = providers.generate_json(
            'Return exactly this JSON: {"ok": true}'
        )
        duration = time.time() - start
        if not result.get("success"):
            return False, f"AI provider error: {result.get('error', 'unknown')}"
        data = result.get("data") or {}
        if data.get("ok") is True:
            return True, f"AI provider responded in {duration:.1f}s"
        return False, f"AI returned unexpected payload: {data}"
    except Exception as e:
        return False, f"AI check raised: {e}"


def check_search():
    try:
        start = time.time()
        results = providers.search_web("openai", max_results=1)
        duration = time.time() - start
        if results and len(results) >= 1:
            return True, f"search provider returned {len(results)} result(s) in {duration:.1f}s"
        return False, f"search provider returned no results in {duration:.1f}s"
    except Exception as e:
        return False, f"search check raised: {e}"


def check_fetch():
    try:
        from stages import fetch
        start = time.time()
        # A stable, content-rich URL. Wikipedia is a good canary because
        # it's always up, its HTML is standard, and trafilatura reliably
        # extracts a large amount of text from it.
        result = fetch.fetch_source("https://en.wikipedia.org/wiki/OpenAI")
        duration = time.time() - start
        if result.get("success") and result.get("content"):
            word_count = result.get("word_count", 0)
            return True, f"fetcher extracted {word_count} words in {duration:.1f}s"
        return False, (
            f"fetcher failed on https://en.wikipedia.org/wiki/OpenAI: "
            f"{result.get('error', 'unknown')} ({result.get('status')})"
        )
    except Exception as e:
        return False, f"fetch check raised: {e}"


# --- Runner ------------------------------------------------------------

CHECKS = [
    ("database", check_database),
    ("search",   check_search),
    ("fetch",    check_fetch),
]

AI_CHECKS = [
    ("ai",       check_ai),
]


def run_all(include_ai=False):
    checks = list(CHECKS)
    if include_ai:
        checks += AI_CHECKS

    results = {}
    for name, fn in checks:
        logger.info(f"health: running {name} check")
        try:
            ok, msg = fn()
        except Exception as e:
            ok, msg = False, f"unhandled exception: {e}"
            logger.error(traceback.format_exc())
        results[name] = {"ok": ok, "message": msg}
        status = "OK" if ok else "FAIL"
        logger.info(f"health: [{status}] {name}: {msg}")

    return results


def _print_summary(results):
    print()
    print("=" * 60)
    print("Health check summary")
    print("=" * 60)
    for name, r in results.items():
        marker = "[OK]  " if r["ok"] else "[FAIL]"
        print(f"  {marker} {name:10s} {r['message']}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-ai", action="store_true",
                        help="Also run the AI provider check (uses quota)")
    args = parser.parse_args()

    results = run_all(include_ai=args.with_ai)
    _print_summary(results)

    all_ok = all(r["ok"] for r in results.values())
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()