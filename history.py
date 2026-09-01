# history.py (placeholder for now)
def format_history(research_list):
    lines = []
    for r in research_list:
        lines.append(f"ID {r['id']}: {r['topic'][:50]} - {r['status']} ({r['created_at']})")
    return "\n".join(lines)