import logging
import utils
import prompts
import providers

logger = utils.logger

# Weights for the deterministic final score.
# These can be tuned later; keep them explicit so they are auditable.
WEIGHTS = {
    'relevance':    0.30,
    'quality':      0.25,
    'evidence':     0.20,
    'recency':      0.10,
    'bias':         0.10,
    'completeness': 0.05,
}

MIN_RELEVANCE = 40          # source must be at least this relevant
MIN_FINAL_SCORE = 50        # source must reach this final score to be verified


def verify_sources(sources, research_context):
    """
    Verify a list of sources in one AI call.
    Final scores are calculated deterministically in Python.
    """
    if not sources:
        return []

    sources_text = ""
    for i, s in enumerate(sources):
        sources_text += (
            f"\n--- Source {i+1} ---\n"
            f"Title: {s.get('title','')}\n"
            f"Domain: {s.get('domain','')}\n"
            f"Snippet: {s.get('snippet','')}\n"
            f"URL: {s.get('url','')}\n"
        )

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
        except (KeyError, IndexError, TypeError):
            results.append({"status": "verification_failed", "error": "Malformed response"})
            continue

        # Deterministic final score
        final_score = (
            item.get('relevance_score', 0)    * WEIGHTS['relevance'] +
            item.get('quality_score', 0)      * WEIGHTS['quality'] +
            item.get('evidence_score', 0)     * WEIGHTS['evidence'] +
            item.get('recency_score', 0)      * WEIGHTS['recency'] +
            item.get('bias_score', 0)         * WEIGHTS['bias'] +
            item.get('completeness_score', 0) * WEIGHTS['completeness']
        )
        item['final_score'] = round(final_score, 2)

        # Verification decision
        relevant = item.get('relevant', False)
        enough_relevance = item.get('relevance_score', 0) >= MIN_RELEVANCE
        enough_score = item['final_score'] >= MIN_FINAL_SCORE

        if relevant and enough_relevance and enough_score:
            item['status'] = 'verified'
        else:
            item['status'] = 'rejected'

        results.append(item)
    return results