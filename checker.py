import logging
import utils
import prompts
import gemini
import providers

logger = utils.logger

def check_answer(answer, package_content):
    """Fact-check the answer against the research package."""
    prompt = prompts.checker_prompt(answer, package_content)
    result = providers.generate_json(prompt)
    if not result['success']:
        return {"status": "verification_error", "error": result.get('error')}
    data = result['data']
    # Determine if passed
    if data.get('status') == 'passed':
        return {"status": "passed", "claims_checked": data.get('claims_checked', 0),
                "unsupported_claims": [], "partially_supported_claims": []}
    else:
        return {
            "status": "failed",
            "claims_checked": data.get('claims_checked', 0),
            "unsupported_claims": data.get('unsupported_claims', []),
            "partially_supported_claims": data.get('partially_supported_claims', [])
        }