"""LinkedIn comment ghostwriter for FMCG posts.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python comment_helper.py                       # serious tone (default)
    python comment_helper.py --tone funny
    python comment_helper.py --tone contrarian
    python comment_helper.py --tone insider
    python comment_helper.py -t funny < post.txt   # pipe a file
"""

import argparse
import os
import sys
import anthropic

COMMON_RULES = """- No em-dashes, no emojis, no "Great post!" filler
- Avoid AI tells: "delve into", "leveraging", "synergies", "navigate the landscape", "robust", "game-changer", "ever-evolving", "deep dive", "moreover", "unpack", "tapestry"
- Sound like a real human FMCG professional, not corporate AI"""

TONE_PROMPTS = {
    "serious": f"""You write LinkedIn comments for someone in the FMCG sector (food, beverages, confectionery, cosmetics).

Given the LinkedIn post below, write THREE distinct comment options. Each must:

- Be 2 to 3 sentences, max 60 words
- Add real value: a specific stat, counter-angle, brand example, or sharp question
{COMMON_RULES}

Use a DIFFERENT angle for each:
- Option A (ADD CONTEXT): cite a stat, brand example, or industry move that extends the post's point
- Option B (FRIENDLY DISAGREEMENT): respectful counter-take, defended with a specific reason
- Option C (OPEN QUESTION): a sharp, specific question that invites the author to expand

Format your reply EXACTLY like this, no preamble:

OPTION A (add context):
<comment>

OPTION B (friendly disagreement):
<comment>

OPTION C (open question):
<comment>""",

    "funny": f"""You write SHORT FUNNY LinkedIn comments for someone in the FMCG sector (food, beverages, confectionery, cosmetics).

Given the LinkedIn post below, write THREE short witty comment options. Each must:

- Be MAX 25 words
- Be genuinely witty: a sharp deadpan observation, a cultural callback, or a one-liner
- Sound like an industry insider, not random meme humor
- Reference the specific brand, product, or topic, not generic humor
- Avoid the obvious joke everyone else makes
{COMMON_RULES}
- No "lol", "haha", or "this is gold"

Use a DIFFERENT angle for each:
- Option A (CHEEKY OBSERVATION): deadpan industry-insider take catching the absurdity
- Option B (CULTURAL CALLBACK): reference a meme, movie, song, or trend that fits the post
- Option C (IN-CHARACTER): comment in the voice of a relevant character, brand persona, or archetype

Format your reply EXACTLY:

OPTION A (cheeky observation):
<comment>

OPTION B (cultural callback):
<comment>

OPTION C (in-character):
<comment>""",

    "contrarian": f"""You write LinkedIn comments that respectfully PUSH BACK on the post's main claim. The user works in FMCG (food, beverages, confectionery, cosmetics).

Given the LinkedIn post below, write THREE distinct counter-takes. Each must:

- Be 2 to 3 sentences, max 60 words
- Challenge the post's premise from a specific, defensible angle
- Stay respectful, no snark
- Use a real stat, brand example, or counter-trend to back the claim
{COMMON_RULES}

Use a DIFFERENT angle for each:
- Option A (NUMBERS COUNTER): cite a specific stat or trend that contradicts the post
- Option B (WRONG QUESTION): argue the post is asking the wrong question, propose the right one
- Option C (OPPOSITE OUTCOME): predict the trend will go the other way, with one specific reason

Format your reply EXACTLY:

OPTION A (numbers counter):
<comment>

OPTION B (wrong question):
<comment>

OPTION C (opposite outcome):
<comment>""",

    "insider": f"""You write data-heavy LinkedIn comments for someone in the FMCG sector (food, beverages, confectionery, cosmetics).

Given the LinkedIn post below, write THREE comments that each add a different kind of industry context. Each must:

- Be 2 to 3 sentences, max 60 words
- Cite something specific: a brand move, a real number, or a recent industry event
- Sound like someone who reads the trades weekly (Just Food, The Grocer, Cosmetics Business)
{COMMON_RULES}

Use a DIFFERENT angle for each:
- Option A (BRAND MOVE): cite what a specific named brand recently did related to the topic
- Option B (HARD STAT): cite a specific number, percentage, or growth figure
- Option C (RECENT EVENT): reference a recent M&A, launch, regulation, or earnings call

Format your reply EXACTLY:

OPTION A (brand move):
<comment>

OPTION B (hard stat):
<comment>

OPTION C (recent event):
<comment>""",
}


def main():
    parser = argparse.ArgumentParser(description="Generate LinkedIn comment options for an FMCG post.")
    parser.add_argument(
        "-t", "--tone",
        choices=list(TONE_PROMPTS.keys()),
        default="serious",
        help="Tone of the comments (default: serious)",
    )
    args = parser.parse_args()

    if sys.stdin.isatty():
        print(
            f"Tone: {args.tone}\n"
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

    full_prompt = TONE_PROMPTS[args.tone] + f"\n\nThe LinkedIn post:\n\"\"\"\n{post}\n\"\"\""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": full_prompt}],
    )
    print()
    print(message.content[0].text)


if __name__ == "__main__":
    main()
