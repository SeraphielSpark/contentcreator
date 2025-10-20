from flask import Flask, request, jsonify
from flask_cors import CORS
import cohere

app = Flask(__name__)
CORS(app)

# Initialize Cohere client
co = cohere.Client(api_key="QRrRqcMgcV4Ecn5PDTeRM2skjfGvgkoXwM2UaP1T")

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
    app.run(debug=True)

