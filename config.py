import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate required
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in .env")

# Concurrency limits
MAX_RESEARCH_JOBS = 3
MAX_SOURCE_FETCHES = 5
MAX_SEARCHES = 5
MAX_AI_REQUESTS = 3

# Database file
DB_PATH = "researchbot.db"

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")

# Gemini model settings
GEMINI_MODEL = "gemini-3.1-flash-lite"
GEMINI_TEMPERATURE = 0.2
GEMINI_MAX_OUTPUT_TOKENS = 4096