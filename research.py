import logging
import utils
from core.database import get_or_create_user, create_research
from core import worker

logger = utils.logger


def research(request, user_telegram_id: str, progress_callback=None):
    """
    Create a research job from a ResearchRequest and start it.

    Args:
        request: ResearchRequest instance
        user_telegram_id: Telegram user ID (string)
        progress_callback: optional callable(research_id, stage) for progress updates

    Returns:
        research_id (int)
    """
    user_id = get_or_create_user(user_telegram_id)
    research_id = create_research(user_id, request.topic)

    worker.start_research(
        research_id,
        progress_callback,
        profile=request.profile(),
    )

    return research_id