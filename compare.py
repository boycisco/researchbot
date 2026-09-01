import logging
from difflib import SequenceMatcher
import utils
import prompts
import gemini

logger = utils.logger

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_candidate_pairs(claims, threshold=0.6):
    """Find pairs of claims that are similar enough to warrant AI comparison."""
    pairs = []
    n = len(claims)
    for i in range(n):
        for j in range(i+1, n):
            # Only compare claims from different sources (source_id differs)
            if claims[i]['source_id'] != claims[j]['source_id']:
                sim = similarity(claims[i]['claim'], claims[j]['claim'])
                if sim >= threshold:
                    pairs.append((claims[i], claims[j], sim))
    return pairs

def compare_claims(claim_a, claim_b):
    """Use Gemini to determine relationship between two claims."""
    prompt = prompts.comparison_prompt(claim_a['claim'], claim_b['claim'])
    result = gemini.generate_json(prompt)
    if not result['success']:
        return None
    return result['data']