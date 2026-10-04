import json
import logging
import utils
from database import get_sources_for_research, get_claims, get_relationships

logger = utils.logger

def build_package(research, sources, claims, relationships, queries):
    """Build a research package JSON string from verified data."""
    verified_sources = [s for s in sources if s['verification_status'] == 'verified']

    # ---------- Sources ----------
    source_list = []
    for s in verified_sources:
        source_list.append({
            'id': s['id'],
            'url': s['url'],
            'canonical_url': s['canonical_url'],
            'title': s['title'],
            'domain': s['domain'],
            'source_type': s['source_type'],
            'is_primary': bool(s['is_primary']),
            'quality_score': s['quality_score'],
            'relevance_score': s['relevance_score'],
        })

    # Safety dedup: keep only the first occurrence of each canonical URL
    _seen_canonical = set()
    deduped_sources = []
    for src in source_list:
        key = src.get('canonical_url') or src.get('url')
        if key in _seen_canonical:
            continue
        _seen_canonical.add(key)
        deduped_sources.append(src)
    source_list = deduped_sources

    # ---------- Search strategy ----------
    search_strategy = []
    for q in queries:
        search_strategy.append({
            'query': q['query'],
            'purpose': q['purpose'] or '',
            'priority': q['priority'],
        })

    # ---------- Statistics ----------
    statistics = []
    for c in claims:
        if c['claim_type'] == 'statistic':
            statistics.append({
                'claim': c['claim'],
                'evidence': c['evidence'],
                'source_id': c['source_id'],
            })

    # ---------- Contradictions & contexts ----------
    from stages.compare import detect_contradictions
    classified = detect_contradictions(claims, relationships)
    contradictions     = classified['true_contradictions']
    different_contexts = classified['different_contexts']
    qualifiers         = classified['qualifiers']

    # ---------- Source → claims map ----------
    source_claim_map = {}
    for c in claims:
        sid = c['source_id']
        if sid not in source_claim_map:
            source_claim_map[sid] = []
        source_claim_map[sid].append(c['id'])

    # ---------- Limitations ----------
    limitations = []
    if len(verified_sources) < 3:
        limitations.append("Limited number of verified sources.")
    if contradictions:
        limitations.append("Conflicting evidence found.")
    domains = [s['domain'] for s in verified_sources if s['domain']]
    if len(set(domains)) <= 1 and domains:
        limitations.append("Most sources come from a single domain, reducing independence.")
    primary_count = sum(1 for s in verified_sources if s['is_primary'])
    if primary_count == 0:
        limitations.append("No primary sources were identified.")

    # ---------- Source URL lookup for claims ----------
    source_url_by_id = {s['id']: s['url'] for s in verified_sources}

    # ---------- Package ----------
    package = {
        'user_question':   research['topic'],
        'research_intent': research['intent'] or '',
        'main_topic':      research['topic'],

        'search_strategy': search_strategy,

        'key_findings': [
            c['claim'] for c in claims
            if (c['confidence_score'] or 0) >= 70
        ][:5],

        'claims': [{
            'id':                    c['id'],
            'claim':                 c['claim'],
            'claim_type':            c['claim_type'],
            'evidence':              c['evidence'],
            'source_id':             c['source_id'],
            'source_url':            source_url_by_id.get(c['source_id'], ''),
            'ai_confidence':         c['confidence'],
            'confidence_score':      c['confidence_score'],
            'confidence_level':      c['confidence_level'],
            'confidence_explanation': c['confidence_explanation'],
        } for c in claims],

        'statistics':         statistics,
        'contradictions':     contradictions,
        'different_contexts': different_contexts,
        'qualifiers':         qualifiers,
        'limitations':        limitations,

        'source_claim_map':   source_claim_map,
        'sources':            source_list,
    }
    return json.dumps(package, indent=2)