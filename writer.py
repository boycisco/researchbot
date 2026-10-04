import logging
import re
import utils
import prompts
import providers

logger = utils.logger

# Patterns to strip from the model output if they leak through
_LEAK_PATTERNS = [
    re.compile(r'^\s*CITATION FORMAT\s*:.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*STRICT RULES?\s*:.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'【[^】]*】'),
    re.compile(r'⟦[^⟧]*⟧'),
    re.compile(r'\{\{[^}]*\}\}'),
    re.compile(r'^\s*#{1,6}\s+', re.MULTILINE),
]


def clean_answer(text):
    """Strip leaked prompt artifacts from the writer's output."""
    if not text:
        return text
    cleaned = text
    for pat in _LEAK_PATTERNS:
        cleaned = pat.sub('', cleaned)
    # Collapse excessive blank lines left behind
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def write_answer(package_content, original_question, intent):
    """Generate final answer using Gemini, based on research package."""
    prompt = prompts.writer_prompt(package_content, original_question, intent)
    result = providers.generate_text(prompt)
    if not result['success']:
        logger.error(f"Writer failed: {result.get('error')}")
        return None
    return clean_answer(result['text'])