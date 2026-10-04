import re

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

def split_message(text, max_len=TELEGRAM_MAX_MESSAGE_LENGTH):
    """Split text into chunks respecting paragraph boundaries and avoiding cutting words/URLs."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = ""
    for line in text.split('\n'):
        # If adding this line would exceed limit, flush current chunk
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current.strip())
                current = ""
            # If line itself is too long, split further by words
            while len(line) > max_len:
                # Find a good break point (space) near max_len
                break_point = line.rfind(' ', 0, max_len)
                if break_point == -1:
                    break_point = max_len
                chunks.append(line[:break_point].strip())
                line = line[break_point:].strip()
            current = line
        else:
            if current:
                current += '\n' + line
            else:
                current = line
    if current:
        chunks.append(current.strip())
    # Filter empty chunks
    return [c for c in chunks if c]

def format_progress(stage):
    emoji_map = {
        'analysis': '🔎 Understanding your question...',
        'query_generation': '🔎 Planning search strategy...',
        'search': '🌐 Searching the web...',
        'fetching': '📚 Fetching sources...',
        'verification': '📚 Reviewing sources...',
        'claim_extraction': '🔬 Checking evidence...',
        'confidence': '📊 Scoring evidence...',
        'comparison': '🧠 Cross-checking findings...',
        'packaging': '📦 Organizing research...',
        'writing': '✍️ Writing the answer...',
        'fact_checking': '🔍 Fact-checking...',
        'completed': '✅ Research complete.',
        'failed': '❌ Research failed.',
        'cancelled': '🛑 Research cancelled.'
    }
    return emoji_map.get(stage, 'Processing...')