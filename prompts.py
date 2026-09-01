def analysis_prompt(topic):
    return f"""
You are a research analyst. Given a user's research topic, produce a structured analysis.

Topic: "{topic}"

Return JSON with:
- main_topic: string, the core subject
- research_question: string, the most important question to answer
- intent: string, likely user intent (e.g., "informational", "comparison", "fact_check")
- subtopics: list of strings, important subtopics to cover
- information_needed: list of strings, types of evidence needed
- search_angles: list of strings, different angles for searching (e.g., "recent developments", "statistics", "expert opinions")
Do not include any markdown, only JSON.
"""

def query_prompt(analysis_json, max_queries=8):
    return f"""
Given this research analysis:
{analysis_json}

Generate a set of diverse search queries to gather comprehensive evidence.
Queries should cover:
- direct answer
- recent developments
- primary evidence
- statistics
- expert/research findings
- counterarguments
- historical context if relevant

Constraints:
- Maximum {max_queries} queries.
- Remove duplicates and near-duplicates.
- Each query should be distinct in purpose.
- Use specific terms, not vague phrases.

Return JSON:
{{"queries": [{{"query": "...", "purpose": "...", "priority": 1}}]}}
Only JSON.
"""

def verification_prompt(source_info, research_context):
    return f"""
You are a source verifier for a research project.
Research topic: {research_context}

Source details:
Title: {source_info.get('title', '')}
Domain: {source_info.get('domain', '')}
Snippet: {source_info.get('snippet', '')}
URL: {source_info.get('url', '')}
(Note: full content may be provided separately if needed)

Evaluate the source based on:
- relevance to the research topic
- quality (authority, credibility)
- evidence quality (data, citations)
- recency
- primary source status
- source type

Return JSON:
{{
  "relevant": true/false,
  "relevance_score": 0-100,
  "quality_score": 0-100,
  "evidence_score": 0-100,
  "recency_score": 0-100,
  "source_type": "government|academic|research_institution|primary_source|news|organization|company|blog|forum|other",
  "is_primary": true/false,
  "reason": "brief explanation"
}}
Only JSON.
"""

def claims_prompt(source_content, research_question):
    return f"""
Extract factual claims relevant to this research question: "{research_question}"

Source content (first 5000 chars):
{source_content[:5000]}

For each claim, provide:
- claim: the factual statement
- claim_type: fact|finding|statistic|historical|quote|opinion|interpretation
- evidence: direct supporting text from the source (verbatim if possible)
- support_level: strong|moderate|weak
- confidence: 0-100 (your confidence that this claim is accurately represented)

Return JSON list of claims:
{{"claims": [{{"claim": "...", "claim_type": "...", "evidence": "...", "support_level": "...", "confidence": 80}}]}}
Only include claims that are relevant and supported by the source. Do not invent claims.
Only JSON.
"""

def comparison_prompt(claim_a, claim_b):
    return f"""
You are comparing two claims from different sources to determine their relationship.

Claim A: "{claim_a}"
Claim B: "{claim_b}"

Determine if they support each other, contradict, partially support, are related, or unrelated.
Return JSON:
{{
  "relationship": "supports|contradicts|partially_supports|related|unrelated",
  "reason": "brief explanation",
  "confidence": 0-100
}}
Only JSON.
"""

def writer_prompt(package_content, original_question, intent):
    return f"""
You are a research writer. Write a comprehensive answer to the user's question using ONLY the provided research package.

User question: {original_question}
Intent: {intent}

Research package (JSON):
{package_content}

Instructions:
- Answer directly and clearly.
- Prioritize high-confidence findings.
- Distinguish facts from opinions.
- Acknowledge contradictions and limitations.
- Cite sources using numbers [1], [2], etc., matching the source list.
- Do NOT introduce any external information not present in the package.
- Structure:
   Quick Answer
   Key Findings
   Detailed Explanation
   Evidence
   Different Perspectives
   Limitations
   Conclusion
   Sources (list all sources used)
Return plain text (not markdown), with clear section headers.
"""

def checker_prompt(answer, package_content):
    return f"""
You are a fact checker. Given the answer and the research package, verify if all factual claims in the answer are supported by the package.

Answer:
{answer}

Research package (JSON):
{package_content}

Extract all factual claims from the answer. For each claim, determine if it is supported, partially supported, or unsupported by the research package.
Return JSON:
{{
  "status": "passed" or "failed",
  "claims_checked": number,
  "unsupported_claims": [{{"claim": "...", "reason": "..."}}],
  "partially_supported_claims": [{{"claim": "...", "reason": "..."}}]
}}
If there are no unsupported or partially supported claims, status should be "passed".
Only JSON.
"""

def batch_verification_prompt(sources_text, research_context):
    return f"""
You are a source verifier for a research project.
Research topic: {research_context}

Below are {sources_text.count('--- Source')} sources. For each source, evaluate relevance, quality, evidence quality, recency, primary source status, and source type.
Return JSON in this exact format:
{{
  "sources": [
    {{
      "relevant": true/false,
      "relevance_score": 0-100,
      "quality_score": 0-100,
      "evidence_score": 0-100,
      "recency_score": 0-100,
      "source_type": "government|academic|research_institution|primary_source|news|organization|company|blog|forum|other",
      "is_primary": true/false,
      "reason": "brief explanation"
    }},
    ... one object per source, in the same order
  ]
}}
Sources:
{sources_text}
Only JSON.
"""

def batch_claims_prompt(sources_text, research_question):
    return f"""
Extract factual claims relevant to this research question: "{research_question}"

Below are several sources with their IDs and content. For each source, identify and extract up to 3 important factual claims (only those relevant to the question). For each claim, provide:
- source_id: the numeric ID of the source (as shown in the source header)
- claim: the factual statement
- claim_type: fact|finding|statistic|historical|quote|opinion|interpretation
- evidence: direct supporting text from the source (verbatim if possible)
- support_level: strong|moderate|weak
- confidence: 0-100

Return JSON:
{{
  "claims": [
    {{"source_id": 1, "claim": "...", "claim_type": "...", "evidence": "...", "support_level": "...", "confidence": 80}},
    ...
  ]
}}
Only include claims that are relevant and supported by the source. Do not invent claims.
Only JSON.

Sources:
{sources_text}
"""