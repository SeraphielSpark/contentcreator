import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai

# ------------------------------------------------------------------
# 0.  ENVIRONMENT
# ------------------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
PORT = int(os.getenv("PORT", 8000))

if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in environment variables!")

# ------------------------------------------------------------------
# 1.  GOOGLE GENAI CLIENT
# ------------------------------------------------------------------
client = genai.Client(api_key=API_KEY)

# ------------------------------------------------------------------
# 2.  FLASK APP  +  CORS
# ------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # allow all origins (change if you need tighter rules)

# ------------------------------------------------------------------
# 3.  ROUTE
# ------------------------------------------------------------------
@app.route("/generate", methods=["POST"])
def generate_hashtags():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify(error="Content is required"), 400

    prompt = (
        "Extract 10 SEO-friendly hashtags from the following content. "
        "Return hashtags only, separated by commas.\n\n"
        f'Content: "{content}"'
    )

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        generated_text = response.text.strip() if response.text else ""
    except Exception as e:
        print("Gemini API error:", e)
        return jsonify(error="Generation failed"), 500

    hashtags = [
        tag.strip()
        for tag in generated_text.replace("\n", ",").split(",")
        if tag.strip().startswith("#")
    ]
    return jsonify(hashtags=hashtags)

# ------------------------------------------------------------------
# 4.  LOCAL DEV ENTRY-POINT
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
