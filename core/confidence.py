import logging
import utils

logger = utils.logger

# Weights sum to 1.0
WEIGHTS = {
    'ai_confidence':  0.40,   # the extraction confidence from claims.py
    'source_quality': 0.30,   # avg quality_score of supporting sources
    'independence':   0.15,   # distinct domains / total supporting
    'recency':        0.10,   # avg recency_score of supporting sources
    'primary_source': 0.05,   # 100 if any supporting source is primary
}

CONTRADICTION_PENALTY = 20   # subtracted per true contradiction


def _level(score):
    if score >= 90:
        return "Very High"
    if score >= 70:
        return "High"
    if score >= 40:
        return "Moderate"
    return "Low"


def compute_confidence(claim, claims, relationships, sources_by_id):
    """
    Compute a deterministic confidence score for a single claim.

    claim:           sqlite3.Row or dict with at least id, source_id, confidence
    claims:          list of all claims for the research
    relationships:   list of all relationships for the research
    sources_by_id:   dict mapping source_id -> source row
    """
    claim_id = claim['id']
    own_source_id = claim['source_id']

    supporting_source_ids = {own_source_id}
    contradicting_source_ids = set()

    for r in relationships:
        a = r['claim_a']
        b = r['claim_b']
        rel = r['relationship']

        if a == claim_id:
            other_id = b
        elif b == claim_id:
            other_id = a
        else:
            continue

        other_claim = next((c for c in claims if c['id'] == other_id), None)
        if not other_claim:
            continue

        other_source_id = other_claim['source_id']

        if rel in ('supports', 'partially_supports'):
            supporting_source_ids.add(other_source_id)
        elif rel == 'contradicts':
            contradicting_source_ids.add(other_source_id)

    supporting_sources = [sources_by_id[sid] for sid in supporting_source_ids if sid in sources_by_id]
    contradicting_sources = [sources_by_id[sid] for sid in contradicting_source_ids if sid in sources_by_id]

    total_supporting = len(supporting_sources)
    avg_quality = 0.0
    avg_recency = 0.0
    has_primary = False
    domains = set()

    if supporting_sources:
        quality_vals = [(s['quality_score'] or 0) for s in supporting_sources]
        recency_vals = [(s['recency_score'] or 0) for s in supporting_sources]
        avg_quality = sum(quality_vals) / len(quality_vals)
        avg_recency = sum(recency_vals) / len(recency_vals)
        has_primary = any(s['is_primary'] for s in supporting_sources)
        domains = {s['domain'] for s in supporting_sources if s['domain']}

    distinct_domains = len(domains)
    independence_ratio = (distinct_domains / total_supporting) if total_supporting > 0 else 0.0
    independence_score = independence_ratio * 100

    primary_bonus = 100 if has_primary else 0
    contradiction_count = len(contradicting_sources)

    ai_conf = claim['confidence'] if claim['confidence'] is not None else 50

    raw_score = (
        WEIGHTS['ai_confidence']  * ai_conf +
        WEIGHTS['source_quality'] * avg_quality +
        WEIGHTS['independence']   * independence_score +
        WEIGHTS['recency']        * avg_recency +
        WEIGHTS['primary_source'] * primary_bonus
    ) - CONTRADICTION_PENALTY * contradiction_count

    score = max(0.0, min(100.0, round(raw_score, 1)))
    level = _level(score)

    parts = [f"{total_supporting} supporting source(s)"]
    if distinct_domains:
        parts.append(f"{distinct_domains} distinct domain(s)")
    parts.append(f"average source quality {round(avg_quality)}")
    if has_primary:
        parts.append("includes primary source")
    if contradiction_count:
        parts.append(f"{contradiction_count} contradicting source(s)")
    else:
        parts.append("no contradictions")
    explanation = "Based on " + ", ".join(parts) + "."

    return {
        'score':                     score,
        'level':                     level,
        'explanation':               explanation,
        'supporting_source_count':   total_supporting,
        'contradicting_source_count': contradiction_count,
        'distinct_domains':          distinct_domains,
        'has_primary':               has_primary,
    }