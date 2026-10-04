import logging
import utils
import prompts
import providers

logger = utils.logger

VALID_CLASSIFICATIONS = {
    "supported",
    "partially_supported",
    "unsupported",
    "contradicted",
    "uncertain",
}


def _normalize_findings(raw):
    """Clean up findings from the AI. Only keep well-formed entries."""
    findings = []
    if not isinstance(raw, list):
        return findings
    for item in raw:
        if not isinstance(item, dict):
            continue
        sentence = str(item.get('sentence', '')).strip()
        classification = str(item.get('classification', '')).strip().lower()
        reason = str(item.get('reason', '')).strip()
        if not sentence:
            continue
        if classification not in VALID_CLASSIFICATIONS:
            classification = 'uncertain'
        findings.append({
            'sentence': sentence,
            'classification': classification,
            'reason': reason,
        })
    return findings


def check_answer(answer, package_content):
    """
    Fact-check the answer against the research package.
    Returns:
      {
        "status": "passed" | "failed" | "verification_error",
        "sentences_checked": int,
        "findings": [ ... ],           # every sentence with its classification
        "problematic": [ ... ],        # only the ones that are not "supported"
      }
    """
    prompt = prompts.checker_prompt(answer, package_content)
    result = providers.generate_json(prompt)

    if not result['success']:
        logger.error(f"Fact checker failed: {result.get('error')}")
        return {
            "status": "verification_error",
            "error": result.get('error'),
            "sentences_checked": 0,
            "findings": [],
            "problematic": [],
        }

    data = result['data']
    findings = _normalize_findings(data.get('findings', []))
    problematic = [f for f in findings if f['classification'] != 'supported']

    # Recompute status deterministically — don't trust the model's summary.
    if problematic:
        status = 'failed'
    else:
        status = 'passed'

    return {
        "status": status,
        "sentences_checked": len(findings),
        "findings": findings,
        "problematic": problematic,
    }