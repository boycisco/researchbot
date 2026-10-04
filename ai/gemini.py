import warnings
warnings.filterwarnings("ignore")

import google.generativeai as genai
import json
import re
import time
import threading
import logging
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE, GEMINI_MAX_OUTPUT_TOKENS
import utils

logger = utils.logger

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# Global rate limiter: max 10 calls per minute
class RateLimiter:
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
                logger.info(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                now = time.time()
                self.calls = [t for t in self.calls if now - t < self.period]
            self.calls.append(now)

rate_limiter = RateLimiter(max_calls=10, period=60)

def _generate_with_retry(prompt, temperature=None, max_output_tokens=None, is_json=False, retries=3):
    for attempt in range(retries):
        rate_limiter.wait()
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature if temperature is not None else GEMINI_TEMPERATURE,
                    max_output_tokens=max_output_tokens if max_output_tokens else GEMINI_MAX_OUTPUT_TOKENS,
                )
            )
            if is_json:
                text = response.text
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                if json_match:
                    text = json_match.group(1)
                else:
                    start = text.find('{')
                    end = text.rfind('}')
                    if start != -1 and end != -1:
                        text = text[start:end+1]
                try:
                    data = json.loads(text)
                    return {"success": True, "data": data}
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}, text: {text[:500]}")
                    return {"success": False, "error": "invalid_json"}
            else:
                return {"success": True, "text": response.text}
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                wait_time = 2 ** attempt * 5
                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt+1})")
                time.sleep(wait_time)
            else:
                logger.error(f"Gemini API error: {e}")
                return {"success": False, "error": error_str}
    return {"success": False, "error": "Max retries exceeded"}

def generate_text(prompt, temperature=None, max_output_tokens=None):
    return _generate_with_retry(prompt, temperature, max_output_tokens, is_json=False)

def generate_json(prompt, temperature=None, max_output_tokens=None):
    return _generate_with_retry(prompt, temperature, max_output_tokens, is_json=True)