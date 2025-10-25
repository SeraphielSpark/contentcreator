from flask import Flask, request, jsonify
from google import genai
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize Gemini client using environment variable from Render
API_KEY = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Hashtag Generator API is live!"})

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    post_content = data.get("post", "")

    if not post_content:
        return jsonify({"error": "No post content provided"}), 400

    prompt = f"""
    You are an expert social media strategist.
    The user provided this post caption:
    "{post_content}"

    Your task:
    1. Keep the user's content EXACTLY as it is.
    2. Add a new line below and generate ONLY 7 to 10 trending, aesthetic, SEO-optimized hashtags.
    3. Make sure the hashtags are relevant to the post.
    4. Return the entire output as one full text block — the original post + hashtags below.
    5. Do NOT include explanations or numbering.

    Format output as:

    [Original post caption]

    [7–10 hashtags]
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        result = response.text.strip()
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
