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

def comparison_prompt(claim_a, claim_b, evidence_a="", evidence_b=""):
    return f"""
You are comparing two claims drawn from different sources. Your job is to classify their relationship.

Claim A: {claim_a}
Supporting evidence for A: {evidence_a[:400]}

Claim B: {claim_b}
Supporting evidence for B: {evidence_b[:400]}

Choose exactly one relationship from this list:

- supports
    B provides independent evidence that A is true.

- partially_supports
    B supports part of A but not all of A.

- contradicts
    A and B cannot both be true. Same subject, same timeframe, same population,
    opposite conclusion. This is a TRUE CONTRADICTION.

- qualifies
    B is true only under specific conditions, refining or narrowing A.
    Both can coexist.

- different_context
    A and B appear to conflict, but they refer to different populations,
    definitions, timeframes, methodologies, or scope. Both can be true.

- related
    A and B are on the same topic but are neither agreeing nor disagreeing.

- unrelated
    A and B concern different topics.

Then provide:

- context_notes: a short explanation (1-3 sentences) of WHY you chose this relationship.
  For "different_context" and "qualifies", explicitly state the relevant difference
  (population, date, methodology, definition, etc.).

- confidence: 0-100, how confident you are in this classification.

RULES:
- Be strict about "contradicts". Only use it for genuine, irreconcilable disagreement.
- Do NOT use "contradicts" when the difference is population, timeframe, methodology,
  or definitions. Use "different_context" instead.
- Do NOT invent facts not present in the two claims and their evidence.

Return JSON:
{{
  "relationship": "supports|partially_supports|contradicts|qualifies|different_context|related|unrelated",
  "context_notes": "...",
  "confidence": 0-100
}}

Only JSON.
"""

def writer_prompt(package_content, original_question, intent):
    return f"""
You are a research writer. Write a concise, evidence-based answer to the user's question.

The research package below is your ONLY source of facts. Do not use outside knowledge.
If the package does not contain evidence for something, do not say it.

User question: {original_question}
Intent: {intent}

Research package (JSON):
{package_content}

STRICT RULES:

1. CITATIONS
   - The package contains a "sources" array. Number them 1..N in the order they appear.
   - IGNORE the internal "id" field of each source. Use only 1, 2, 3, ... for citations.
   - Place a citation like [1] or [1, 3] immediately after EACH factual sentence.
   - Do not batch all citations at the end of a paragraph.
   - In the final SOURCES section, list them as:
        [1] <url>
        [2] <url>

2. ACCURACY
   - Every factual sentence must be traceable to a source in the package.
   - Do not invent sources, URLs, statistics, quotes, or claims.
   - If the package contains contradictory claims, mention both sides and cite them.

3. CONFIDENCE
   - Each claim carries "confidence_score" (0-100) and "confidence_level".
   - Use these to calibrate wording:
        Very High → "strong evidence shows", "well-supported"
        High      → "evidence indicates"
        Moderate  → "some evidence suggests"
        Low       → "limited evidence suggests", "one early study found"
   - Never overstate confidence.

4. UNCERTAINTY
   - If evidence is weak or absent, say so plainly. Do not pretend to know.
   - Prefer "research suggests" over "research proves".

5. STYLE
   - Be useful, not exhaustive. Do not dump every claim from the package.
   - Prefer 2-4 paragraphs total. Short sections, no walls of text.
   - No markdown formatting (no **, no ##, no bullet dashes).
     Use plain text; for lists, use a leading "- ".

6. STRUCTURE
   Return plain text with these exact section headers, each on its own line, in uppercase:

       QUICK ANSWER
       KEY FINDINGS
       DETAILED ANALYSIS
       CAVEATS AND LIMITATIONS
       CONCLUSION
       SOURCES

   Under KEY FINDINGS, use a short bullet list (max 5 items), each with a citation.
   Under DETAILED ANALYSIS, 2-3 short paragraphs, each sentence cited.
   Under CAVEATS AND LIMITATIONS, list what is uncertain, contradictory, or missing.
   Under CONCLUSION, 1-2 sentences.
   Under SOURCES, list every source you cited, numbered from 1.

7. FORBIDDEN
   - Do NOT output instructions, meta-commentary, prompt echoes, or placeholders.
   - Do NOT output the string "CITATION FORMAT".
   - Do NOT output anything before QUICK ANSWER or after SOURCES.

Write the answer now.
"""

def checker_prompt(answer, package_content):
    return f"""
You are a strict fact checker. Your job is to verify every factual sentence in the answer against the research package.

Answer to check:
{answer}

Research package (JSON):
{package_content}

RULES:
1. Split the answer into individual factual sentences. Ignore:
   - Section headers (QUICK ANSWER, KEY FINDINGS, etc.)
   - Citation markers like [1], [2, 3]
   - Non-factual sentences (e.g., "This is complex.", "Let me explain.")

2. For EACH factual sentence, classify it as exactly one of:
   - "supported"            — the package contains evidence that directly supports it
   - "partially_supported"  — the package supports part of it, but not all
   - "unsupported"          — the package contains no evidence for it
   - "contradicted"         — the package contains evidence that contradicts it
   - "uncertain"            — the package's evidence is too weak or ambiguous to decide

3. Compare ONLY against the package. Do NOT use outside knowledge.
   If the sentence is true in the real world but not supported by the package,
   classify it as "unsupported" — the rule is package support, not world truth.

4. For every sentence that is NOT "supported", provide a short reason
   quoting or paraphrasing the relevant part of the package (or its absence).

5. Overall status:
   - "passed"  if EVERY factual sentence is "supported"
   - "failed"  if ANY sentence is "partially_supported", "unsupported", or "contradicted"
   - "uncertain" is allowed and does not fail by itself, but report it.

Return JSON in this exact format:
{{
  "status": "passed" | "failed",
  "sentences_checked": <number>,
  "findings": [
    {{
      "sentence": "<the exact sentence from the answer>",
      "classification": "supported" | "partially_supported" | "unsupported" | "contradicted" | "uncertain",
      "reason": "<short explanation; required unless classification is supported>"
    }}
  ]
}}

Only JSON. No commentary outside the JSON.
"""

def batch_verification_prompt(sources_text, research_context):
    return f"""
You are a source verifier for a research project.
Research topic: {research_context}

Below are sources with title, domain, snippet, and URL. For each source, evaluate:

- relevance to the research topic (0-100, higher = more relevant)
- quality of the source as a publication (0-100, based on reputation, authority, editorial standards)
- evidence quality (0-100, does it cite data, studies, primary sources?)
- recency (0-100, 100 = very recent, 0 = outdated or unknown)
- bias_score (0-100, 100 = impartial/factual, 0 = highly biased or promotional)
- completeness_score (0-100, does it cover the topic in depth or just superficially?)
- source_type (one of: government, academic, research_institution, primary_source, news, organization, company, blog, forum, other)
- is_primary (true if this IS the primary source, e.g. original study, official document; false if it merely reports on one)
- reason (brief explanation, 1-2 sentences)

Return JSON in this exact format:
{{
  "sources": [
    {{
      "relevant": true/false,
      "relevance_score": 0-100,
      "quality_score": 0-100,
      "evidence_score": 0-100,
      "recency_score": 0-100,
      "bias_score": 0-100,
      "completeness_score": 0-100,
      "source_type": "...",
      "is_primary": true/false,
      "reason": "..."
    }}
    ... one object per source, in the same order
  ]
}}

Be strict. Do not give high scores out of politeness. A blog post with no evidence should not receive a high evidence_score. A press release should not receive a high bias_score.

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

def revision_prompt(package_content, original_question, intent, problematic_findings):
    findings_text = ""
    for f in problematic_findings:
        findings_text += (
            f"- Sentence: {f['sentence']}\n"
            f"  Classification: {f['classification']}\n"
            f"  Reason: {f['reason']}\n\n"
        )

    return f"""
You are revising a research answer that failed fact-checking.

Original question: {original_question}
Intent: {intent}

Research package (JSON):
{package_content}

The following sentences in your previous answer were NOT fully supported by the package:

{findings_text}

Rewrite the entire answer so that:
1. Every problematic sentence is either:
   - removed, OR
   - rewritten so it is supported by the package.
2. Do NOT add new facts that are not in the package.
3. Do NOT change sentences that were already supported.
4. Keep the same section structure and citation rules as before.
5. If a claim cannot be supported, simply do not include it.

Return the full rewritten answer in plain text, using the same structure:
QUICK ANSWER
KEY FINDINGS
DETAILED ANALYSIS
CAVEATS AND LIMITATIONS
CONCLUSION
SOURCES

Only the answer. No commentary.
"""