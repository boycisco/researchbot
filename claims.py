import logging
import json
import utils
import prompts
import gemini

logger = utils.logger

def extract_claims_batch(sources_with_content, research_question):
    """
    Extract claims from multiple sources in one Gemini call.
    sources_with_content: list of dicts with 'source_id' and 'content'
    Returns list of claims (each with source_id attached).
    """
    if not sources_with_content:
        return []
    sources_text = ""
    for i, s in enumerate(sources_with_content):
        content_snippet = s['content'][:3000]
        sources_text += f"\n--- Source {i+1} (ID: {s['source_id']}) ---\n{content_snippet}\n"
    prompt = prompts.batch_claims_prompt(sources_text, research_question)
    result = gemini.generate_json(prompt)
    if not result['success']:
        logger.error(f"Batch claim extraction failed: {result.get('error')}")
        return []
    data = result['data']
    all_claims = []
    for item in data.get('claims', []):
        if 'source_id' not in item or 'claim' not in item or 'evidence' not in item:
            continue
        claim = item['claim'].strip()
        evidence = item['evidence'].strip()
        if not claim or not evidence:
            continue
        all_claims.append({
            'source_id': item['source_id'],
            'claim': claim,
            'claim_type': item.get('claim_type', 'fact'),
            'evidence': evidence,
            'support_level': item.get('support_level', 'moderate'),
            'confidence': item.get('confidence', 50)
        })
    return all_claims