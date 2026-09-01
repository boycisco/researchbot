import warnings
warnings.filterwarnings("ignore", message=".*metadata extraction.*")
warnings.filterwarnings("ignore", message=".*discarding data.*")

import logging
logging.getLogger("trafilatura").setLevel(logging.ERROR)

import trafilatura
import requests
import logging
from urllib.parse import urlparse
import utils

logger = utils.logger

def fetch_source(url, timeout=20):
    """
    Fetch and extract main content from a URL.
    Returns dict with success, content, word_count, title, published_at, status.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)'}
        resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}", "status": "http_error"}
        html = resp.text
        # Use trafilatura to extract main content
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True, output_format='txt')
        if not extracted:
            return {"success": False, "error": "Extraction failed", "status": "extraction_failed"}
        word_count = utils.calculate_word_count(extracted)
        if word_count < 50:  # too short
            return {"success": False, "error": "Insufficient content", "status": "insufficient_content"}
        # Try to get title and date
        title = trafilatura.extract_metadata(html).title if trafilatura.extract_metadata(html) else ''
        published_at = trafilatura.extract_metadata(html).date if trafilatura.extract_metadata(html) else ''
        return {
            "success": True,
            "content": extracted,
            "word_count": word_count,
            "title": title,
            "published_at": published_at,
            "status": "fetched"
        }
    except requests.Timeout:
        return {"success": False, "error": "Timeout", "status": "timeout"}
    except requests.RequestException as e:
        return {"success": False, "error": str(e), "status": "network_error"}
    except Exception as e:
        logger.error(f"Unexpected fetch error for {url}: {e}")
        return {"success": False, "error": str(e), "status": "unknown_error"}