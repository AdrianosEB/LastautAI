import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def analyze_frame(image_b64: str, clicks: list) -> str:
    """Analyze a screenshot + click list and return a workflow description."""
    if not image_b64:
        return ''

    click_summary = ''
    if clicks:
        click_summary = f'\n\nThe user made {len(clicks)} clicks during this period at these coordinates:\n'
        click_summary += '\n'.join(f"  - x={c.get('x')}, y={c.get('y')}" for c in clicks[:20])

    prompt = (
        "This is a screenshot of the user's screen taken during a recording session."
        " Look at what applications are open, what content is visible, and what the user appears to be doing."
        + click_summary
        + "\n\nIf you can identify a clear repeated workflow or pattern that could be automated, "
        "describe it in 2-3 plain sentences covering what the user is doing and whether it looks automatable. "
        "If there is not enough information to identify a pattern, respond only with: "
        "'Not enough data to identify patterns yet.' "
        "Keep the response concise and non-technical. Do not use bullet points."
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }],
    )

    return next((b.text for b in response.content if b.type == "text"), '')
