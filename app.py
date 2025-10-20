from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import cohere

# --- Flask Setup ---
app = Flask(__name__)

# Allow all origins for public API
CORS(app, resources={r"/ask": {"origins": "*"}})

# --- Securely Load API Key ---
cohere_api_key = os.environ.get("COHERE_API_KEY")

if not cohere_api_key:
    raise ValueError("⚠️ COHERE_API_KEY not found in environment variables!")

# Initialize Cohere client (Render supports latest Cohere SDK)
co = cohere.Client(api_key=cohere_api_key)

# --- Routes ---
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        user_input = data.get("question", "").strip()

        if not user_input:
            return jsonify({"error": "No question provided"}), 400

        # Prompt for Cohere
        prompt = f"""
        Generate 15–20 SEO-optimized hashtags relevant to the following content.
        Each hashtag must start with # and avoid generic tags like #love or #life.
        Separate each hashtag with a space.

        Content:
        "{user_input}"

        Hashtags:
        """

        # --- Use Cohere’s Generate Endpoint (more stable for Render) ---
        response = co.generate(
            model="command-xlarge-nightly",
            prompt=prompt,
            temperature=0.4,
            max_tokens=150
        )

        hashtags_text = response.generations[0].text.strip()

        return jsonify({"generations": [{"text": hashtags_text}]})

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


# --- Entry Point for Render ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns this
    app.run(host="0.0.0.0", port=port)
