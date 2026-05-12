import json
import os
import random
import re
import anthropic
import requests

POST_PROMPT = """You write LinkedIn posts about FMCG trends.

Cover fresh trends across ALL FMCG categories — confectionery, food, beverages, and cosmetics/personal care. Pick ONE category and ONE specific trend per post, with a concrete angle.

Trend areas to draw from:
- Confectionery: sugar reduction, premiumization, dark cocoa surge, functional chocolate, mochi & Asian crossover, mini-format growth
- Food: GLP-1 impact on snacking, protein everywhere, gut health, plant-based plateau, clean-label backlash, hyper-local sourcing
- Beverages: functional drinks (mushroom, adaptogen), low/no alcohol, prebiotic sodas, energy drinks for women, hyper-hydration
- Cosmetics & personal care: skinification of haircare, fragrance boom, biotech ingredients, men's grooming, refillable packaging
- Cross-category: AI in product development, retail media networks, dark stores, sustainability labelling, traceability tech

Rules for the post:
- Maximum 100 words — tight and punchy, every sentence earns its place
- Open with a hook: a surprising stat, a tiny story, or a sharp observation
- Make ONE clear point with substance — specific examples beat vague claims
- Insightful, professional tone — like someone who actually works in FMCG
- No emojis
- 3-5 relevant hashtags at the end
- End with an open question to the audience
- Avoid clichés like "FMCG is changing rapidly" or "consumers are evolving"

Respond ONLY with valid JSON, no markdown fences, in this exact format:
{
  "post": "<full post text including hashtags and question>",
  "image_keyword": "<2-4 word search query for a relevant Pexels stock photo, e.g. 'chocolate bars shelf' or 'cosmetics store'>"
}"""


def generate_post():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": POST_PROMPT}],
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
