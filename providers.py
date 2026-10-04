import config
from ai import gemini
from stages import search
from stages import fetch

# AI Provider
def generate_text(prompt, temperature=None, max_output_tokens=None):
    if config.AI_PROVIDER == "gemini":
        return gemini.generate_text(prompt, temperature, max_output_tokens)
    else:
        raise NotImplementedError(f"AI provider '{config.AI_PROVIDER}' not implemented")

def generate_json(prompt, temperature=None, max_output_tokens=None):
    if config.AI_PROVIDER == "gemini":
        return gemini.generate_json(prompt, temperature, max_output_tokens)
    else:
        raise NotImplementedError(f"AI provider '{config.AI_PROVIDER}' not implemented")

# Search Provider
def search_web(query, max_results=5):
    if config.SEARCH_PROVIDER == "duckduckgo":
        return search.search_web(query, max_results)
    else:
        raise NotImplementedError(f"Search provider '{config.SEARCH_PROVIDER}' not implemented")

# Fetch Provider
def fetch_source(url, timeout=20):
    return fetch.fetch_source(url, timeout)