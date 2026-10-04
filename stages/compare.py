import logging
from difflib import SequenceMatcher
import utils
from ai import prompts
import providers

logger = utils.logger

# Thresholds and caps (tune later if needed)
CLAIM_SIM_THRESHOLD    = 0.45
EVIDENCE_SIM_THRESHOLD = 0.35
MAX_PAIRS              = 40   # cap AI comparisons per research

# Relationships considered "contradictory" for reporting purposes
TRUE_CONTRADICTION = "contradicts"
DIFFERENT_CONTEXT  = "different_context"
QUALIFIES          = "qualifies"


def _get(row, key, default=None):
    """Get a value from a dict or a sqlite3.Row safely."""
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _pair_score(claim_a, claim_b):
    """Combined similarity based on claim text and evidence text."""
    claim_sim = similarity(_get(claim_a, 'claim', ''), _get(claim_b, 'claim', ''))
    ev_a = _get(claim_a, 'evidence', '') or ''
    ev_b = _get(claim_b, 'evidence', '') or ''
    ev_sim = 0.0
    if ev_a and ev_b:
        ev_sim = similarity(ev_a[:500], ev_b[:500])
    return max(claim_sim, ev_sim)


def find_candidate_pairs(claims, max_pairs=MAX_PAIRS):
    """
    Return a list of (claim_a, claim_b, score) for cross-source pairs
    whose similarity exceeds at least one threshold. Sorted by score desc.
    """
    pairs = []
    n = len(claims)
    for i in range(n):
        for j in range(i + 1, n):
            if _get(claims[i], 'source_id') == _get(claims[j], 'source_id'):
                continue

            claim_sim = similarity(_get(claims[i], 'claim', ''), _get(claims[j], 'claim', ''))
            ev_a = _get(claims[i], 'evidence', '') or ''
            ev_b = _get(claims[j], 'evidence', '') or ''
            ev_sim = 0.0
            if ev_a and ev_b:
                ev_sim = similarity(ev_a[:500], ev_b[:500])

            if claim_sim >= CLAIM_SIM_THRESHOLD or ev_sim >= EVIDENCE_SIM_THRESHOLD:
                score = max(claim_sim, ev_sim)
                pairs.append((claims[i], claims[j], score))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:max_pairs]


def compare_claims(claim_a, claim_b):
    """Ask the AI to classify the relationship between two claims."""
    prompt = prompts.comparison_prompt(
        _get(claim_a, 'claim', ''),
        _get(claim_b, 'claim', ''),
        evidence_a=_get(claim_a, 'evidence', '') or '',
        evidence_b=_get(claim_b, 'evidence', '') or '',
    )
    result = providers.generate_json(prompt)
    if not result['success']:
        logger.error(f"Claim comparison failed: {result.get('error')}")
        return None
    data = result['data']

    allowed = {
        "supports", "partially_supports", "contradicts",
        "qualifies", "different_context", "related", "unrelated"
    }
    relationship = str(data.get('relationship', 'unrelated')).lower()
    if relationship not in allowed:
        relationship = 'related'

    try:
        confidence = float(data.get('confidence', 50))
    except (TypeError, ValueError):
        confidence = 50.0

    return {
        'relationship':  relationship,
        'reason':        data.get('context_notes', ''),
        'confidence':    confidence,
    }


def detect_contradictions(claims, relationships):
    """
    Classify stored relationships into three buckets:
        - true_contradictions
        - different_contexts
        - qualifiers
    """
    claim_by_id = {_get(c, 'id'): c for c in claims}

    true_contradictions = []
    different_contexts  = []
    qualifiers          = []

    for r in relationships:
        claim_a = claim_by_id.get(_get(r, 'claim_a'))
        claim_b = claim_by_id.get(_get(r, 'claim_b'))
        if not claim_a or not claim_b:
            continue

        entry = {
            'claim_a':    _get(claim_a, 'claim', ''),
            'claim_b':    _get(claim_b, 'claim', ''),
            'source_a':   _get(claim_a, 'source_id'),
            'source_b':   _get(claim_b, 'source_id'),
            'reason':     _get(r, 'reason', '') or '',
            'confidence': _get(r, 'confidence', 0) or 0,
        }

        rel = _get(r, 'relationship', '')
        if rel == TRUE_CONTRADICTION:
            true_contradictions.append(entry)
        elif rel == DIFFERENT_CONTEXT:
            different_contexts.append(entry)
        elif rel == QUALIFIES:
            qualifiers.append(entry)

    return {
        'true_contradictions': true_contradictions,
        'different_contexts':  different_contexts,
        'qualifiers':          qualifiers,
    }