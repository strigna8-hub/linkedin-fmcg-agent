import datetime
import json
import os
import random
import re
import anthropic
import requests

HISTORY_FILE = "post_history.json"
HISTORY_LOOKBACK = 10
HISTORY_MAX = 30

WEEKDAY_CATEGORIES = {
    0: ("confectionery", "Confectionery: sugar reduction, premiumization, dark cocoa surge, functional chocolate, mochi/Asian crossover, mini-format growth"),
    1: ("food", "Food: GLP-1 impact on snacking, protein everywhere, gut health, plant-based plateau, clean-label backlash, hyper-local sourcing"),
    2: ("beverages", "Beverages: functional drinks (mushroom, adaptogen), low/no alcohol, prebiotic sodas, energy drinks for women, hyper-hydration"),
    3: ("cosmetics", "Cosmetics & personal care: skinification of haircare, fragrance boom, biotech ingredients, men's grooming, refillable packaging"),
    4: ("fast food", "Fast food & QSR: McDonald's, Burger King, KFC, Starbucks, Chick-fil-A, Subway, Domino's — value menu wars, viral LTOs, healthier reformulations, GLP-1 impact on traffic, chicken vs beef wars, breakfast battles, app/loyalty economics"),
}

POST_FORMATS = {
    "case_study": "FORMAT — MINI CASE STUDY. Structure: one brand, one specific recent move from the news, the surprising number behind it, what it signals for the category. One narrative thread. Tight and concrete.",
    "stat_bomb": "FORMAT — STAT BOMB. Open with a one-line hook, then stack 3-4 punchy numbers (one per line, no fluff between them) tied to the story or the category right now. Close with a one-line takeaway, then the question. Numbers should make people stop scrolling.",
    "prediction": "FORMAT — PREDICTION. Make a bold, falsifiable call about where this category goes in the next 6-12 months. Back the prediction with the actual current signal you found in the news. End the question framed as agree/disagree.",
    "listicle": "FORMAT — LISTICLE. Frame as '3 things happening in [category] right now' or similar. Three crisp bullets (use '-' or numbers), each with a real brand or specific stat. Then a one-line closer and the question.",
}

WRITING_STYLES = [
    "conversational — like texting a smart friend, contractions, casual rhythm",
    "blunt and journalistic — no fluff, short declarative sentences, reporter tone",
    "analytical and slightly dry — numbers-forward, treat it like an analyst note",
    "witty and a touch sarcastic — dry humor, no try-hard energy",
    "punchy and pop-culture aware — references that land, modern voice",
]

BASE_PROMPT = """You write LinkedIn posts about FMCG trends that actually drive engagement.

TODAY'S CATEGORY: {category_name}
TODAY'S TREND AREAS: {category_trends}

POST FORMAT FOR THIS RUN: {post_format}

WRITING STYLE FOR THIS POST: Write in a voice that is {writing_style}. The voice should feel distinct — not the generic LinkedIn-thought-leader register.

Today is {today}. Use the web_search tool to find ONE specific, recent news story, launch, deal, earnings note, or trend from the LAST 14 DAYS within {category_name}. Search terms like "{category_name} news {month_year}", "{category_name} launch", "{category_name} trend", or a specific brand + recent. Pick a story that's concrete and recent — not generic evergreen content.

AVOID these recent topics (already covered in the last {history_count} posts):
{avoid_list}

CRITICAL ENGAGEMENT RULES (follow all):

1. HOOK. The first sentence must stop the scroll — only ~210 characters of the post show before LinkedIn's "see more" cutoff. Open with a specific number, a contrarian claim, or a tiny story. Forbidden openers: "In today's", "FMCG is", "The world of", "As we", "It's no secret", "Did you know".

2. CONCRETE. Every post must name at least one real brand from the news you found AND/OR include a specific stat with a number. Reference the actual news event you found.

3. FORMATTING. Use short lines. Each sentence on its own line. Break ideas with blank lines between mini-paragraphs. Walls of text kill engagement on LinkedIn.

4. BANNED PHRASES (they scream "AI wrote this"): "Moreover", "delve into", "navigate the landscape", "in today's fast-paced", "leveraging", "synergies", "robust", "game-changer", "ever-evolving", "paradigm shift", "deep dive", "unpack", "tapestry". Use em-dashes sparingly — max ONE per post.

5. CLOSING QUESTION. Must be a forced-choice or strong-opinion prompt. NOT "What do you think?" or "Curious to hear your thoughts." Examples: "Is shrinkflation theft or inflation in disguise?", "Better 2026 bet: prebiotic sodas or non-alc spirits?", "Would you pay £8 for a chocolate bar?"

6. LENGTH. Max 100 words total. Tight beats long.

7. NO EMOJIS. None.

8. HASHTAGS. 3-5 relevant ones on a single line after a blank line.

{mode_directive}

After researching, respond with your FINAL ANSWER as valid JSON only (no markdown fences, no preamble). Preserve line breaks inside the post string as \\n:
{{
  "post": "<full post text with \\n line breaks, including hashtags and question>",
  "image_keyword": "<2-4 word Pexels search query, e.g. 'chocolate bars shelf' or 'cosmetics store'>",
  "topic": "<5-10 word summary of the specific topic/story this post covers, for history tracking>"
}}"""

CONTRARIAN_DIRECTIVE = """9. CONTRARIAN MODE (apply this run): Challenge a popular FMCG belief or consensus view. Argue against the mainstream take. Be provocative but defensible — back the contrarian claim with a specific reason or example."""

POLITICAL_HUMOR_DIRECTIVE = """9. POLITICAL POP-CULTURE ANGLE (apply this run): Hook the post around a famous moment where a politician or world leader intersected with a food, beverage, fast-food, or consumer brand — e.g. Trump's McDonald's order, Obama's beer summit, Macron's protein routine, Boris Johnson's fridge moments, world leader photo-ops at brands. Connect the joke back to the actual news story you found. Be observational and witty, not partisan or mean — the joke should make smart people across the political spectrum smile. No insults to specific politicians, no taking sides."""


def pick_category():
    weekday = datetime.datetime.utcnow().weekday()
    return WEEKDAY_CATEGORIES.get(weekday, WEEKDAY_CATEGORIES[1])


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
        return data.get("posts", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_history(posts):
    trimmed = posts[-HISTORY_MAX:]
    with open(HISTORY_FILE, "w") as f:
        json.dump({"posts": trimmed}, f, indent=2)


def build_avoid_list(history):
    recent = history[-HISTORY_LOOKBACK:]
    if not recent:
        return "(none yet — this is one of the first posts)"
    return "\n".join(f"- [{p.get('date', '?')}, {p.get('category', '?')}] {p.get('topic', '?')}" for p in recent)


def pick_mode_directive():
    roll = random.random()
    if roll < 0.25:
        return "contrarian", CONTRARIAN_DIRECTIVE
    if roll < 0.50:
        return "political_humor", POLITICAL_HUMOR_DIRECTIVE
    return "neutral", ""


def pick_format():
    name = random.choice(list(POST_FORMATS.keys()))
    return name, POST_FORMATS[name]


def build_post_prompt(category_name, category_trends, history):
    mode_name, mode_directive = pick_mode_directive()
    format_name, format_directive = pick_format()
    writing_style = random.choice(WRITING_STYLES)
    today = datetime.date.today()
    prompt = BASE_PROMPT.format(
        category_name=category_name,
        category_trends=category_trends,
        post_format=format_directive,
        writing_style=writing_style,
        today=today.isoformat(),
        month_year=today.strftime("%B %Y"),
        history_count=min(len(history), HISTORY_LOOKBACK),
        avoid_list=build_avoid_list(history),
        mode_directive=mode_directive,
    )
    return prompt, {"format": format_name, "style": writing_style, "mode": mode_name}


def generate_post(category_name, category_trends, history):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    prompt, choices = build_post_prompt(category_name, category_trends, history)
    print(f"Format: {choices['format']} | Mode: {choices['mode']}")
    print(f"Writing style: {choices['style']}")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    text_chunks = [b.text for b in message.content if b.type == "text"]
    full_text = "\n".join(text_chunks)

    matches = list(re.finditer(r"\{[^{}]*\"post\"[^{}]*\"image_keyword\"[^{}]*\}", full_text, re.DOTALL))
    if not matches:
        matches = list(re.finditer(r"\{.*?\}", full_text, re.DOTALL))
    if not matches:
        raise ValueError(f"No JSON object in model response. Got:\n{full_text}")

    last_json = matches[-1].group(0)
    result = json.loads(last_json)
    result["_choices"] = choices
    return result


def fetch_pexels_image(keyword, api_key):
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        params={"query": keyword, "per_page": 5, "orientation": "landscape"},
        headers={"Authorization": api_key},
        timeout=20,
    )
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        return None
    photo = random.choice(photos)
    image_url = photo["src"]["large"]
    image_resp = requests.get(image_url, timeout=30)
    image_resp.raise_for_status()
    return image_resp.content


def upload_image_to_linkedin(image_bytes, author_urn, token):
    register_resp = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author_urn,
                "serviceRelationships": [
                    {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                ],
            }
        },
        timeout=30,
    )
    register_resp.raise_for_status()
    data = register_resp.json()["value"]
    upload_url = data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = data["asset"]

    upload_resp = requests.put(
        upload_url,
        data=image_bytes,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    upload_resp.raise_for_status()
    return asset_urn


def post_to_linkedin(content, image_bytes=None):
    token = os.environ["LINKEDIN_ACCESS_TOKEN"].strip()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    profile = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=20)
    profile.raise_for_status()
    user_id = profile.json()["sub"]
    author_urn = f"urn:li:person:{user_id}"

    share_content = {
        "shareCommentary": {"text": content},
        "shareMediaCategory": "NONE",
    }

    if image_bytes:
        asset_urn = upload_image_to_linkedin(image_bytes, author_urn, token)
        share_content = {
            "shareCommentary": {"text": content},
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "description": {"text": "FMCG trend illustration"},
                    "media": asset_urn,
                    "title": {"text": "FMCG"},
                }
            ],
        }

    post_data = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data, timeout=30
    )
    response.raise_for_status()
    print("Post published successfully!")


if __name__ == "__main__":
    category_name, category_trends = pick_category()
    history = load_history()
    print(f"Today's category: {category_name}")
    print(f"History entries loaded: {len(history)}")

    result = generate_post(category_name, category_trends, history)
    post_text = result["post"]
    image_keyword = result.get("image_keyword", "")
    topic = result.get("topic", "(no topic recorded)")
    print(f"Topic: {topic}")

    image_bytes = None
    pexels_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if pexels_key and image_keyword:
        try:
            image_bytes = fetch_pexels_image(image_keyword, pexels_key)
            if image_bytes:
                print(f"Fetched Pexels image for keyword: {image_keyword}")
            else:
                print(f"No Pexels results for keyword: {image_keyword}")
        except Exception as e:
            print(f"Image fetch failed, posting without image: {e}")
    else:
        print("Pexels key or keyword missing — posting text only")

    post_to_linkedin(post_text, image_bytes)

    choices = result.get("_choices", {})
    history.append({
        "date": datetime.date.today().isoformat(),
        "category": category_name,
        "topic": topic,
        "image_keyword": image_keyword,
        "format": choices.get("format"),
        "style": choices.get("style"),
        "mode": choices.get("mode"),
    })
    save_history(history)
    print(f"History updated. Total entries: {len(history)}")
