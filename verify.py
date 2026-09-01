import logging
import json
import utils
import prompts
import gemini
import providers

logger = utils.logger

def verify_sources(sources, research_context):
    """
    Verify a list of sources in one Gemini call.
    sources: list of dicts with keys title, domain, snippet, url, etc.
    Returns list of verification results aligned with input order.
    """
    if not sources:
        return []
    # Prepare a compact prompt listing all sources
    sources_text = ""
    for i, s in enumerate(sources):
        sources_text += f"\n--- Source {i+1} ---\nTitle: {s.get('title','')}\nDomain: {s.get('domain','')}\nSnippet: {s.get('snippet','')}\nURL: {s.get('url','')}\n"
    prompt = prompts.batch_verification_prompt(sources_text, research_context)
    result = providers.generate_json(prompt)
    if not result['success']:
        logger.error(f"Batch verification failed: {result.get('error')}")
        return []
    data = result['data']
    results = []
    for i, s in enumerate(sources):
        try:
            item = data['sources'][i]
        except (KeyError, IndexError):
            results.append({"status": "verification_failed", "error": "Malformed response"})
            continue
        weights = {'relevance': 0.4, 'quality': 0.3, 'evidence': 0.2, 'recency': 0.1}
        final_score = (
            item.get('relevance_score', 0) * weights['relevance'] +
            item.get('quality_score', 0) * weights['quality'] +
            item.get('evidence_score', 0) * weights['evidence'] +
            item.get('recency_score', 0) * weights['recency']
        )
        item['final_score'] = round(final_score, 2)
        item['status'] = 'verified' if item.get('relevant') and final_score >= 50 else 'rejected'
        results.append(item)
    return results