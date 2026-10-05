def format_history(research_list, limit=10):
    """
    Format a list of research rows for Telegram.

    Args:
        research_list: list of sqlite3.Row or dict-like objects with
                       keys: id, topic, status
        limit:         max entries to show

    Returns:
        A plain-text string, ready for Telegram (no markdown).
    """
    if not research_list:
        return "You have no research history."

    lines = []
    for r in research_list[:limit]:
        topic = (r["topic"] or "").strip()
        if len(topic) > 60:
            topic = topic[:57] + "..."
        lines.append(f"ID {r['id']}: {topic} — {r['status']}")

    if len(research_list) > limit:
        lines.append(f"... and {len(research_list) - limit} more.")

    return "\n".join(lines)