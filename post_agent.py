import os
import anthropic
import requests

POST_PROMPT = """Write a LinkedIn post for someone working in the FMCG food sector.

Pick ONE of these three topic areas at random and dig into a specific, concrete angle within it. Do NOT write a generic overview — pick a sharp angle.

1. Health & nutrition trends in FMCG food
   Examples: GLP-1 drugs reshaping snacking, the protein craze, gut-health products, sugar reduction, functional beverages, clean-label backlash, plant-based plateau, etc.

2. Digital & supply chain in FMCG
   Examples: AI in demand forecasting, dark stores, last-mile economics, quick-commerce profitability, retail media networks, automation in warehouses, traceability tech, etc.

3. Everyday observations from the FMCG aisle (relatable + lightly funny)
   Examples: shrinkflation noticed at the supermarket, absurd packaging claims ("now with 20% less air!"), bizarre product names, the psychology of end-cap displays, weird flavor launches, the eternal mystery of "natural flavors", etc.

Rules for the post:
- 150-200 words
- Open with a hook: a surprising stat, a tiny story, or a sharp observation
- Make ONE clear point with substance — specific examples beat vague claims
- Tone:
   • For topics 1 & 2: insightful and specific. Sound like someone who actually works in the industry.
   • For topic 3: warm, witty, gently self-aware. Professional but human — like a smart person noticing something funny on a Tuesday grocery run. Not corporate-speak.
- No emojis
- 3-5 hashtags at the end
- End with an open question to the audience
- Vary the topic and angle from typical LinkedIn FMCG content — avoid clichés like "FMCG is changing rapidly" or "consumers are evolving"."""

def generate_post():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": POST_PROMPT}]
    )
    return message.content[0].text

def post_to_linkedin(content):
    token = os.environ["LINKEDIN_ACCESS_TOKEN"].strip()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    profile = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
    profile.raise_for_status()
    user_id = profile.json()["sub"]
    post_data = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
    response.raise_for_status()
    print("Post published successfully!")

if __name__ == "__main__":
    content = generate_post()
    post_to_linkedin(content)
