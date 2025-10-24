from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import google.generativeai as genai

# --- Flask Setup ---
app = Flask(__name__)

# Allow all origins for public API
CORS(app, resources={r"/ask": {"origins": "*"}})

# --- Securely Load API Key ---
# Note: Changed variable name to GEMINI_API_KEY
gemini_api_key = os.environ.get("COHERE_API_KEY")

if not gemini_api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not found in environment variables!")

# --- Initialize Gemini Client ---
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash-latest')
generation_config = genai.types.GenerationConfig(
    temperature=0.4,
    max_output_tokens=150
)

# --- Routes ---
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        user_input = data.get("question", "").strip()

        if not user_input:
            return jsonify({"error": "No question provided"}), 400

        # Prompt for Gemini (identical to the Cohere one)
        prompt = f"""
        Generate 15–20 SEO-optimized hashtags relevant to the following content.
        Each hashtag must start with # and avoid generic tags like #love or #life.
        Separate each hashtag with a space.

        Content:
        "{user_input}"

        Hashtags:
        """

        # --- Use Gemini's Generate Content Endpoint ---
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )

        hashtags_text = response.text.strip()

        # --- Return in the *exact same* format as the original Cohere API ---
        return jsonify({"generations": [{"text": hashtags_text}]})

    except Exception as e:
        print("Error:", e)
        # Handle potential Gemini-specific errors if needed
        if hasattr(response, 'prompt_feedback'):
            print("Prompt Feedback:", response.prompt_feedback)
            return jsonify({"error": "Content generation failed due to safety filters."}), 500
        
        return jsonify({"error": str(e)}), 500


# --- Entry Point for Render ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns this
    app.run(host="0.0.0.0", port=port)
