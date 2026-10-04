import re
import logging
import time
from threading import Semaphore
from ddgs import DDGS
import utils
from ai import prompts
import providers

logger = utils.logger

# Global semaphore for search requests (thread-safe)
search_semaphore = Semaphore(5)  # max concurrent searches

def generate_queries(analysis_json, max_queries=8):
    """Use Gemini to generate search queries based on analysis."""
    prompt = prompts.query_prompt(analysis_json, max_queries)
    result = providers.generate_json(prompt)
    if not result['success']:
        logger.error("Query generation failed")
        return None
    queries = result['data'].get('queries', [])
    # Clean and deduplicate
    cleaned = []
    seen = set()
    for q in queries:
        query_text = q.get('query', '').strip()
        if not query_text:
            continue
        # Normalize for dedup: lowercase, remove punctuation
        norm = re.sub(r'[^\w\s]', '', query_text.lower())
        norm = ' '.join(norm.split())
        if norm in seen:
            continue
        seen.add(norm)
        cleaned.append({
            'query': query_text,
            'purpose': q.get('purpose', ''),
            'priority': q.get('priority', 1)
        })
    # If more than max_queries, keep highest priority (lower number = higher)
    cleaned.sort(key=lambda x: x['priority'])
    return cleaned[:max_queries]

def search_web(query, max_results=5):
    """Perform a web search using DuckDuckGo (no API key needed)."""
    with search_semaphore:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                normalized = []
                for r in results:
                    url = r.get('href')
                    if not url:
                        continue
                    title = r.get('title', '')
                    snippet = r.get('body', '')
                    if utils.is_probably_junk(title, snippet, url):
                        continue
                    normalized.append({
                        'title': title,
                        'url': url,
                        'canonical_url': utils.normalize_url(url),
                        'domain': utils.get_domain(url),
                        'snippet': snippet,
                        'rank': len(normalized) + 1
                    })
                return normalized
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []