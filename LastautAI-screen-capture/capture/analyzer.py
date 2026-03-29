import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


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

Analyze this activity and identify any repeated sequences, patterns, or workflows.
If you detect a clear pattern, describe it in 2-3 plain sentences covering:
- What the user is doing
- How often the pattern appears
- Whether it looks like something that could be automated

If there are no clear patterns yet, respond only with:
"Not enough data to identify patterns yet."

Keep the response concise and non-technical. Do not use bullet points."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    return next((b.text for b in response.content if b.type == "text"), '')
