import os
import anthropic
import requests

def generate_post():
      client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
      message = client.messages.create(
          model="claude-sonnet-4-6",
          max_tokens=1024,
          messages=[
              {
                  "role": "user",
                  "content": """Write a professional LinkedIn post about the FMCG food sector.

Topics to rotate between:
- Latest trends in FMCG food industry
- Consumer behavior shifts in food and beverages
- Sustainability and packaging innovations
- Health and wellness food trends
- Supply chain insights in food sector
- New product launches and market opportunities
- Digital transformation in FMCG

Requirements:
- 150-200 words
- Professional but engaging tone
- Include 3-5 relevant hashtags at the end
- No emojis
- End with a thought-provoking question to drive engagement"""
              }
          ]
      )
      return message.content[0].text

def post_to_linkedin(content):
      token = os.environ["LINKEDIN_ACCESS_TOKEN"]
      headers = {
          "Authorization": f"Bearer {token}",
          "Content-Type": "application/json"
      }
      profile = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
      profile.raise_for_status()
      user_id = profile.json()["sub"]
      post_data = {
          "author": f"urn:li:person:{user_id}",
          "lifecycleState": "PUBLISHED",
          "specificContent": {
              "com.linkedin.ugc.ShareContent": {
                  "shareCommentary": {
                      "text": content
                  },
                  "shareMediaCategory": "NONE"
              }
          },
          "visibility": {
              "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
          }
      }
      response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=post_data)
      response.raise_for_status()
      print("Post published successfully!")
      print(f"Post content:\n{content}")

if __name__ == "__main__":
      content = generate_post()
      post_to_linkedin(content)
