import logging
import time
import hashlib
import sys
import config
from urllib.parse import urlparse

# Logging setup
def setup_logging():
    """Configure logging with a clean format and no sensitive data."""
    # Optional: enable ANSI colors on Windows
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass

    class SensitiveDataFilter(logging.Filter):
        """Redact sensitive tokens from log records."""
        def filter(self, record):
            if hasattr(config, 'TELEGRAM_BOT_TOKEN'):
                record.msg = str(record.msg).replace(config.TELEGRAM_BOT_TOKEN, "***")
                if record.args:
                    record.args = tuple(str(arg).replace(config.TELEGRAM_BOT_TOKEN, "***") for arg in record.args)
            return True

    # Basic format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Apply filter to root logger
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(SensitiveDataFilter())

    # Silence noisy third‑party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("google.generativeai").setLevel(logging.WARNING)
    logging.getLogger("primp").setLevel(logging.ERROR)
    logging.getLogger("ddgs").setLevel(logging.ERROR)
    logging.getLogger("ddgs.ddgs").setLevel(logging.ERROR)
    logging.getLogger("hickory_net").setLevel(logging.ERROR)
    logging.getLogger("trafilatura").setLevel(logging.ERROR)

    return logging.getLogger("researchbot")

logger = setup_logging()

def normalize_url(url):
    """Basic URL normalization: strip fragments, lower scheme/host, remove trailing slash."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'
    return f"{scheme}://{netloc}{path}"

def get_domain(url):
    return urlparse(url).netloc

def calculate_word_count(text):
    return len(text.split())

def is_probably_junk(title, snippet, url):
    """Heuristic junk filter."""
    junk_phrases = ['login', 'sign up', 'captcha', '404', 'error', 'not found']
    combined = f"{title} {snippet} {url}".lower()
    for p in junk_phrases:
        if p in combined:
            return True
    return False

def safe_truncate(text, max_len=10000):
    return text[:max_len] if len(text) > max_len else text

def now_timestamp():
    return time.time()