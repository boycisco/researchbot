import warnings
warnings.filterwarnings("ignore")

import google.generativeai as genai
import concurrent.futures
import json
import re
import time
import threading

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_OUTPUT_TOKENS,
    MAX_AI_REQUESTS,
    AI_REQUEST_TIMEOUT_S,
)
import utils

logger = utils.logger

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)


# --- Rate limiter --------------------------------------------------------

class RateLimiter:
    """Simple rolling-window rate limiter (max_calls per `period` seconds)."""
    def __init__(self, max_calls, period=60):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0]) + 0.1
                logger.info(f"[ai] rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = time.time()
                self.calls = [t for t in self.calls if now - t < self.period]
            self.calls.append(now)


rate_limiter = RateLimiter(max_calls=MAX_AI_REQUESTS, period=60)


# --- Retry classification ------------------------------------------------

def _classify_error(error_str):
    """
    Return (kind, retriable) where kind is a short label.
    kinds: rate_limit, timeout, server_error, client_error, unknown
    """
    low = error_str.lower()
    if "429" in error_str or "quota" in low or "rate limit" in low:
        return "rate_limit", True
    if ("timeout" in low or "deadline" in low or "timed out" in low
            or "exceeded" in low):
        return "timeout", True
    if "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
        return "server_error", True
    if "400" in error_str or "401" in error_str or "403" in error_str or "404" in error_str:
        return "client_error", False
    return "unknown", False


def _parse_retry_delay(error_str, default=10):
    """
    Extract the retry delay from a Google API error string.
    Google provides it in two forms:
        "Please retry in 31.648219527s."
        "retry_delay { seconds: 31 }"
    Return the larger of what we find, or `default`.
    """
    # Form 1: "retry in X.Ys"
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str)
    if m:
        return float(m.group(1))
    # Form 2: "retry_delay { seconds: N }"
    m = re.search(r"seconds:\s*(\d+)", error_str)
    if m:
        return float(m.group(1))
    return default


def _call_sdk(prompt, temperature, max_output_tokens):
    """Raw SDK call. Runs in a helper thread so we can enforce a timeout."""
    return model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature if temperature is not None else GEMINI_TEMPERATURE,
            max_output_tokens=max_output_tokens if max_output_tokens else GEMINI_MAX_OUTPUT_TOKENS,
        ),
    )


def _call_with_timeout(prompt, temperature, max_output_tokens, timeout_s):
    """
    Run the SDK call in a separate thread. If it doesn't return within
    timeout_s, abandon it and raise TimeoutError.

    The abandoned thread keeps running in the background until the SDK
    call finishes; Python cleans it up when the process exits.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_call_sdk, prompt, temperature, max_output_tokens)
    try:
        result = future.result(timeout=timeout_s)
        executor.shutdown(wait=False)
        return result
    except concurrent.futures.TimeoutError:
        logger.warning(f"[ai] SDK call exceeded {timeout_s}s; abandoning thread")
        executor.shutdown(wait=False, cancel_futures=True)
        raise TimeoutError(f"AI call exceeded {timeout_s}s")

# --- Core call ----------------------------------------------------------

def _generate_with_retry(prompt, temperature=None, max_output_tokens=None,
                        is_json=False, retries=3):
    for attempt in range(retries):
        rate_limiter.wait()

        start = time.time()
        try:
            response = _call_with_timeout(
                prompt, temperature, max_output_tokens, AI_REQUEST_TIMEOUT_S
            )
            duration = time.time() - start
            logger.info(f"[ai] call ok attempt={attempt+1} duration={duration:.1f}s json={is_json}")

            if is_json:
                text = response.text
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    text = json_match.group(1)
                else:
                    start_idx = text.find('{')
                    end_idx = text.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        text = text[start_idx:end_idx+1]
                try:
                    data = json.loads(text)
                    return {"success": True, "data": data}
                except json.JSONDecodeError as e:
                    logger.error(f"[ai] json decode error: {e} | text_preview={text[:200]!r}")
                    return {"success": False, "error": "invalid_json"}
            else:
                return {"success": True, "text": response.text}

        except Exception as e:
            duration = time.time() - start
            error_str = str(e)
            kind, retriable = _classify_error(error_str)

            if retriable and attempt < retries - 1:
                if kind == "rate_limit":
                    wait_time = _parse_retry_delay(error_str, default=30) + 2
                else:
                    wait_time = min(2 ** attempt * 5, 60)
                logger.warning(
                    f"[ai] {kind} (attempt {attempt+1}, duration={duration:.1f}s); "
                    f"retrying in {wait_time:.1f}s"
                )
                time.sleep(wait_time)
                continue

            logger.error(
                f"[ai] giving up after {attempt+1} attempt(s) "
                f"(kind={kind}, duration={duration:.1f}s): {error_str[:300]}"
            )
            return {"success": False, "error": error_str}

    return {"success": False, "error": "max_retries_exceeded"}


# --- Public API ---------------------------------------------------------

def generate_text(prompt, temperature=None, max_output_tokens=None):
    return _generate_with_retry(prompt, temperature, max_output_tokens, is_json=False)


def generate_json(prompt, temperature=None, max_output_tokens=None):
    return _generate_with_retry(prompt, temperature, max_output_tokens, is_json=True)