import os
import anthropic
import requests

def generate_post():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Write a professional LinkedIn post about the FMCG food sector. Cover topics like trends, consumer behavior, sustainability, health food trends, supply chain, or digital transformation. Write 150-200 words, professional tone, include 3-5 hashtags at the end, no emojis, end with a question."}]
    )
    return message.content[0].text

def post_to_linkedin(content):
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
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
