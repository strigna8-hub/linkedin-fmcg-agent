import json
import os
import random
import re
import anthropic
import requests

BASE_PROMPT = """You write LinkedIn posts about FMCG trends that actually drive engagement.

Cover fresh trends across ALL FMCG categories — confectionery, food, beverages, cosmetics/personal care. Pick ONE category and ONE specific trend per post.

Trend areas to draw from:
- Confectionery: sugar reduction, premiumization, dark cocoa surge, functional chocolate, mochi/Asian crossover, mini-format growth
- Food: GLP-1 impact on snacking, protein everywhere, gut health, plant-based plateau, clean-label backlash, hyper-local sourcing
- Beverages: functional drinks (mushroom, adaptogen), low/no alcohol, prebiotic sodas, energy drinks for women, hyper-hydration
- Cosmetics & personal care: skinification of haircare, fragrance boom, biotech ingredients, men's grooming, refillable packaging
- Cross-category: AI in product development, retail media networks, dark stores, sustainability labelling, traceability tech

CRITICAL ENGAGEMENT RULES (follow all):

1. HOOK. The first sentence must stop the scroll — only ~210 characters of the post show before LinkedIn's "see more" cutoff. Open with a specific number, a contrarian claim, or a tiny story. Forbidden openers: "In today's", "FMCG is", "The world of", "As we", "It's no secret", "Did you know".

2. CONCRETE. Every post must name at least one real brand (e.g. Nestlé, L'Oréal, Coca-Cola, Unilever, Mondelez, P&G, PepsiCo, Estée Lauder, Mars, Danone, Kraft Heinz, AB InBev, Diageo, Reckitt, Mondelēz, Ferrero, Haribo) AND/OR include a specific stat with a number.

3. FORMATTING. Use short lines. Each sentence on its own line. Break ideas with blank lines between mini-paragraphs. Walls of text kill engagement on LinkedIn.

4. BANNED PHRASES (they scream "AI wrote this"): "Moreover", "delve into", "navigate the landscape", "in today's fast-paced", "leveraging", "synergies", "robust", "game-changer", "ever-evolving", "paradigm shift", "deep dive", "unpack", "tapestry". Use em-dashes sparingly — max ONE per post.

5. CLOSING QUESTION. Must be a forced-choice or strong-opinion prompt. NOT "What do you think?" or "Curious to hear your thoughts." Examples: "Is shrinkflation theft or inflation in disguise?", "Better 2026 bet: prebiotic sodas or non-alc spirits?", "Would you pay £8 for a chocolate bar?"

6. LENGTH. Max 100 words total. Tight beats long.

7. NO EMOJIS. None.

8. HASHTAGS. 3-5 relevant ones on a single line after a blank line.

{mode_directive}

Respond ONLY with valid JSON, no markdown fences. Preserve line breaks inside the post string as \\n:
{{
  "post": "<full post text with \\n line breaks, including hashtags and question>",
  "image_keyword": "<2-4 word Pexels search query, e.g. 'chocolate bars shelf' or 'cosmetics store'>"
}}"""

CONTRARIAN_DIRECTIVE = """9. CONTRARIAN MODE (apply this run): Challenge a popular FMCG belief or consensus view. Argue against the mainstream take. Be provocative but defensible — back the contrarian claim with a specific reason or example."""


def build_post_prompt():
    mode = CONTRARIAN_DIRECTIVE if random.random() < 0.33 else ""
    return BASE_PROMPT.replace("{mode_directive}", mode)


def generate_post():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": build_post_prompt()}],
    )
    response_text = message.content[0].text
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in model response: {response_text}")
    return json.loads(match.group(0))


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
    result = generate_post()
    post_text = result["post"]
    image_keyword = result.get("image_keyword", "")

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
