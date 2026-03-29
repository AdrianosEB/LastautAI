"""
Pattern analyzer — sends event batches to Claude Haiku for analysis.
Ported from LastautAI-screen-capture/capture/analyzer.py.
"""

from src.utils.ai_client import get_client


def analyze_events(events: list) -> str:
    """Send a batch of captured events to Claude and return a workflow description."""
    if not events:
        return ''

    log_lines = '\n'.join(
        f"{e['timestamp']} [{e['event_type']}] {e['app_name']}"
        + (f" — {e['window_title']}" if e['window_title'] else '')
        + (f" ({e['detail']})" if e['detail'] else '')
        for e in events
    )

    prompt = f"""The following is a log of a user's recent computer activity captured over the past few minutes.

{log_lines}

Your job is to identify the IMPORTANT, repeatable workflow the user is performing — not every little action.

Rules:
- IGNORE: random clicks, mouse movements, brief app glances, navigating menus, scrolling, window management
- FOCUS ON: the core task the user is accomplishing across apps (e.g. copying data from one app to another, a multi-step process they repeat, moving information between tools)
- Identify the HIGH-LEVEL goal: what is the user trying to achieve? What is the end result?
- Think about what steps in this process could actually be automated with an n8n workflow (API calls, webhooks, scheduled tasks, data transforms, notifications)

Describe the automation workflow in 2-3 plain sentences covering:
1. The repeatable task the user is doing (the big picture, not individual clicks)
2. A practical automation that could handle this task automatically using triggers, API integrations, and actions

Only respond with "Not enough data to identify patterns yet." if the events show no meaningful task (e.g. just idle app switches with no clear purpose).

Keep the response concise and non-technical. Do not use bullet points. Focus on what matters, skip the noise."""

    response = get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return next((b.text for b in response.content if b.type == "text"), '')


def summarize_suggestion(description: str) -> str:
    """Generate a short plain-language title for a workflow suggestion."""
    if not description:
        return ''
    response = get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=60,
        messages=[{"role": "user", "content": f"""Summarize this workflow suggestion in one short sentence (max 12 words).
Write it as a simple action, like "Auto-create calendar events from Gmail" or "Send Slack alerts when files change".

Suggestion: "{description}"

Return ONLY the short sentence, nothing else."""}],
    )
    return next((b.text for b in response.content if b.type == "text"), '').strip('" ')
