import sys
import time
import argparse
from request import ResearchRequest, DEPTH_PROFILES
import research
from core import database


def main():
    parser = argparse.ArgumentParser(description="Run a research job from the terminal.")
    parser.add_argument("topic", nargs="+", help="The research topic")
    parser.add_argument(
        "--depth",
        choices=list(DEPTH_PROFILES.keys()),
        default="standard",
        help="Research depth (default: standard)",
    )
    args = parser.parse_args()

    topic = " ".join(args.topic).strip()
    if not topic:
        print("Error: empty topic")
        return 1

    database.init_db()

    recovered = database.recover_stale_jobs(max_age_minutes=30)
    if recovered:
        print(f"Recovered {recovered} stale research job(s)")

    def progress_callback(research_id, stage):
        print(f"[Research {research_id}] Stage: {stage}")

    request = ResearchRequest(topic=topic, depth=args.depth)

    print(f"Starting research ({args.depth}): {topic}")
    research_id = research.research(
        request,
        user_telegram_id="cli_user",
        progress_callback=progress_callback,
    )

    while True:
        job = database.get_research(research_id)
        if job and job['status'] in ('completed', 'failed', 'cancelled'):
            print(f"\nFinal status: {job['status']}")
            if job['status'] == 'completed':
                answer = database.get_answer(research_id)
                if answer:
                    print("\n--- ANSWER ---")
                    print(answer['content'])
            elif job['status'] == 'failed':
                print(f"Error: {job['error']}")
            break
        time.sleep(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())