import warnings
import logging
import requests
import trafilatura
from urllib.parse import urlparse
import utils

# Suppress trafilatura warnings
logging.getLogger("trafilatura").setLevel(logging.ERROR)

def fetch_source(url, timeout=20):
    """
    Fetch and extract main content from a URL.
    Returns dict with success, content, word_count, title, published_at, status, http_status.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)'}
        resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        http_status = resp.status_code
        if http_status != 200:
            return {
                "success": False,
                "error": f"HTTP {http_status}",
                "status": "http_error",
                "http_status": http_status
            }
        html = resp.text
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True, output_format='txt')
        if not extracted:
            return {
                "success": False,
                "error": "Extraction failed",
                "status": "extraction_failed",
                "http_status": http_status
            }
        word_count = utils.calculate_word_count(extracted)
        if word_count < 50:
            return {
                "success": False,
                "error": "Insufficient content",
                "status": "insufficient_content",
                "http_status": http_status
            }
        # Get metadata
        metadata = trafilatura.extract_metadata(html)
        title = metadata.title if metadata else ''
        published_at = metadata.date if metadata else ''
        return {
            "success": True,
            "content": extracted,
            "word_count": word_count,
            "title": title,
            "published_at": published_at,
            "status": "fetched",
            "http_status": http_status,
            "canonical_url": url  # For now, use original URL; canonicalization will be improved later
        }
    except requests.Timeout:
        return {"success": False, "error": "Timeout", "status": "timeout"}
    except requests.RequestException as e:
        return {"success": False, "error": str(e), "status": "network_error"}
    except Exception as e:
        logging.getLogger("researchbot").error(f"Unexpected fetch error for {url}: {e}")
        return {"success": False, "error": str(e), "status": "unknown_error"}