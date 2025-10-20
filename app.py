from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import cohere

app = Flask(__name__)

# ✅ Securely load API key from environment
cohere_api_key = os.environ.get("COHERE_API_KEY")

if not cohere_api_key:
    raise ValueError("⚠️ COHERE_API_KEY not found in environment variables!")

# Initialize client (works for both Client and ClientV2)
co = cohere.Client(api_key=cohere_api_key)


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        user_input = data.get("question", "").strip()

        if not user_input:
            return jsonify({"error": "No question provided"}), 400

        # Build prompt
        prompt = f"""
        Generate 15–20 SEO-optimized hashtags relevant to the following content.
        Each hashtag must start with # and avoid generic tags like #love or #life.
        Separate each hashtag with a space.

        Content:
        "{user_input}"

        Hashtags:
        """

        # Cohere chat call
        response = co.chat(
            model="command-a-03-2025",
            temperature=0.3,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )

        # ✅ Extract assistant text correctly
        assistant_message = response.message
        hashtags_text = ""

        # Combine all text content items from assistant message
        for item in assistant_message.content:
            if item.type == "text":
                hashtags_text += item.text + "\n"

        # Return as JSON
        return jsonify({"generations": [{"text": hashtags_text.strip()}]})

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render will set this automatically
    app.run(host="0.0.0.0", port=port, debug=True)



