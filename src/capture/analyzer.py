"""
Pattern analyzer — sends event batches to Claude Haiku for analysis.
Ported from LastautAI-screen-capture/capture/analyzer.py.
"""

import anthropic

_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment


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

Analyze this activity and suggest a workflow that could automate what the user is doing.
Describe the workflow in 2-3 plain sentences covering:
- What the user is doing (summarize the activity)
- A suggested automation workflow based on this activity

Always provide a suggestion, even if the pattern is simple or only partially clear.
Only respond with "Not enough data to identify patterns yet." if there are fewer than 3 events.

Keep the response concise and non-technical. Do not use bullet points."""

    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return next((b.text for b in response.content if b.type == "text"), '')


def summarize_suggestion(description: str) -> str:
    """Generate a short plain-language title for a workflow suggestion."""
    if not description:
        return ''
    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=60,
        messages=[{"role": "user", "content": f"""Summarize this workflow suggestion in one short sentence (max 12 words).
Write it as a simple action, like "Auto-create calendar events from Gmail" or "Send Slack alerts when files change".

Suggestion: "{description}"

Return ONLY the short sentence, nothing else."""}],
    )
    return next((b.text for b in response.content if b.type == "text"), '').strip('" ')
