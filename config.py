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

# Concurrency limits (overridable via .env)
MAX_RESEARCH_JOBS    = int(os.getenv("MAX_RESEARCH_JOBS", 3))
MAX_SOURCE_FETCHES   = int(os.getenv("MAX_SOURCE_FETCHES", 5))
MAX_SEARCHES         = int(os.getenv("MAX_SEARCHES", 5))
MAX_AI_REQUESTS      = int(os.getenv("MAX_AI_REQUESTS", 4))     # AI calls per minute
AI_REQUEST_TIMEOUT_S = int(os.getenv("AI_REQUEST_TIMEOUT_S", 30))  # per AI call, seconds

# Jobs left in an active state for longer than this (in minutes)
# are considered abandoned and marked as failed on startup.
RECOVERY_MAX_AGE_MINUTES = 30

# Database file
DB_PATH = os.getenv("DB_PATH", "researchbot.db")

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "duckduckgo")

# Gemini model settings
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_TEMPERATURE = 0.2
GEMINI_MAX_OUTPUT_TOKENS = 4096