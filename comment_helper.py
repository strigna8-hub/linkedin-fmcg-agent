"""LinkedIn comment ghostwriter for FMCG posts.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python comment_helper.py              # then paste post, Ctrl-D to submit
    python comment_helper.py < post.txt   # or pipe from a file
"""

import os
import sys
import anthropic

PROMPT_TEMPLATE = """You write LinkedIn comments for someone who works in the FMCG sector (food, beverages, confectionery, cosmetics).

Given the LinkedIn post below, write THREE distinct comment options for them to leave on it.

Each comment must:
- Be 2 to 3 sentences, max 60 words
- Add real value: a specific stat, a counter-angle, a concrete brand example, or a sharp question
- Sound like a human FMCG professional, not corporate AI
- No em-dashes, no emojis, no "Great post!" filler
- Avoid AI tells: "delve into", "leveraging", "synergies", "navigate the landscape", "robust", "game-changer", "ever-evolving", "deep dive", "moreover", "unpack", "tapestry"

Use a DIFFERENT angle for each option:
- Option A (ADD CONTEXT): cite a stat, brand example, or recent industry move that supports and extends the post's point
- Option B (FRIENDLY DISAGREEMENT): respectful counter-take, defended with a specific reason or example
- Option C (OPEN QUESTION): a sharp, specific question that invites the author to expand

Format your reply EXACTLY like this, no preamble, no closing remarks:

OPTION A (add context):
<comment>

OPTION B (friendly disagreement):
<comment>

OPTION C (open question):
<comment>

The LinkedIn post:
\"\"\"
{post}
\"\"\""""


def main():
    if sys.stdin.isatty():
        print(
            "Paste the LinkedIn post text below, then press Ctrl-D (Linux/Mac) "
            "or Ctrl-Z then Enter (Windows):\n",
            file=sys.stderr,
        )
    post = sys.stdin.read().strip()
    if not post:
        print("No post text provided.", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Run: export ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(post=post)}],
    )
    print()
    print(message.content[0].text)


if __name__ == "__main__":
    main()
