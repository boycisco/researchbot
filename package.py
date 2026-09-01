import json
import logging
import utils
from database import get_sources_for_research, get_claims, get_relationships

logger = utils.logger

def build_package(research, sources, claims, relationships):
    """Build a research package JSON string from verified data."""
    # Filter sources to those with content and verified
    verified_sources = [s for s in sources if s['verification_status'] == 'verified']
    source_list = []
    for s in verified_sources:
        source_list.append({
            'id': s['id'],
            'url': s['url'],
            'title': s['title'],
            'domain': s['domain'],
            'source_type': s['source_type'],
            'is_primary': s['is_primary'],
            'relevance_score': s['relevance_score'],
            'quality_score': s['quality_score'],
        })
    # Extract statistics from claims where claim_type == 'statistic'
    statistics = []
    for c in claims:
        if c['claim_type'] == 'statistic':
            statistics.append({
                'claim': c['claim'],
                'evidence': c['evidence'],
                'source_id': c['source_id']
            })
    # Contradictions from relationships where relationship == 'contradicts'
    contradictions = []
    for r in relationships:
        if r['relationship'] == 'contradicts':
            claim_a = next((c for c in claims if c['id'] == r['claim_a']), None)
            claim_b = next((c for c in claims if c['id'] == r['claim_b']), None)
            if claim_a and claim_b:
                contradictions.append({
                    'claim_a': claim_a['claim'],
                    'claim_b': claim_b['claim'],
                    'reason': r['reason'],
                    'confidence': r['confidence']
                })
    # Limitations: derive from source count, contradictions, etc.
    limitations = []
    if len(verified_sources) < 3:
        limitations.append("Limited number of verified sources.")
    if contradictions:
        limitations.append("Conflicting evidence found.")
    # Check if many sources are from same domain
    domains = [s['domain'] for s in verified_sources]
    if len(set(domains)) <= 1 and domains:
        limitations.append("Most sources come from a single domain, reducing independence.")
    # Primary sources count
    primary_count = sum(1 for s in verified_sources if s['is_primary'])
    if primary_count == 0:
        limitations.append("No primary sources found.")
    # Recency: check if any source is recent? Hard to determine, skip for now.

    package = {
        'user_question': research['topic'],
        'research_intent': research['intent'] or '',
        'main_topic': research['topic'],
        'key_findings': [c['claim'] for c in claims if c['confidence'] > 70][:5],
        'claims': [{
            'id': c['id'],
            'claim': c['claim'],
            'evidence': c['evidence'],
            'source_id': c['source_id'],
            'confidence': c['confidence']
        } for c in claims],
        'statistics': statistics,
        'contradictions': contradictions,
        'limitations': limitations,
        'sources': source_list
    }
    return json.dumps(package, indent=2)