import logging
import utils
import prompts
import gemini
import providers

logger = utils.logger

def write_answer(package_content, original_question, intent):
    """Generate final answer using Gemini, based on research package."""
    prompt = prompts.writer_prompt(package_content, original_question, intent)
    result = providers.generate_text(prompt)
    if not result['success']:
        return None
    return result['text']