import sys
import time
from request import ResearchRequest
import research
import database

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_research.py <topic>")
        return

    topic = sys.argv[1]

    # Initialize database (runs migrations)
    database.init_db()

    def progress_callback(research_id, stage):
        print(f"[Research {research_id}] Stage: {stage}")

    req = ResearchRequest(topic=topic)
    research_id = research.research(req, user_telegram_id="test_user", progress_callback=progress_callback)

    while True:
        job = database.get_research(research_id)
        if job and job['status'] in ('completed', 'failed', 'cancelled'):
            print(f"\nFinal status: {job['status']}")
            if job['status'] == 'completed':
                answer = database.get_answer(research_id)
                if answer:
                    print("\n--- ANSWER ---")
                    print(answer['content'])
            break
        time.sleep(1)

if __name__ == "__main__":
    main()