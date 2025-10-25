from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import google.generativeai as genai

# --- Flask Setup ---
app = Flask(__name__)

# Allow all origins for public API
CORS(app, resources={r"/ask": {"origins": "*"}})

# --- Securely Load API Key ---
gemini_api_key = os.environ.get("GEMINI_API_KEY")

if not gemini_api_key:
    raise ValueError("⚠️ GEMINI_API_KEY not found in environment variables!")

# --- Initialize Gemini Client ---
try:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    generation_config = genai.types.GenerationConfig(
        temperature=0.4,
        max_output_tokens=150
    )
except Exception as e:
    # This will catch initialization errors if the API key is bad
    print(f"Error initializing Gemini: {e}")
    raise e

# --- Routes ---
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        user_input = data.get("question", "").strip()

        if not user_input:
            return jsonify({"error": "No question provided"}), 400

        # Prompt for Gemini
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
        print(f"Error during content generation: {e}")
        
        # Check if the error is due to safety filters
        try:
            if response.prompt_feedback:
                print("Prompt Feedback:", response.prompt_feedback)
                return jsonify({"error": "Content generation failed. The prompt may have been blocked by safety filters."}), 500
        except Exception:
            pass # response object might not exist if 'model.generate_content' failed

        # General server error
        return jsonify({"error": str(e)}), 500


# --- Entry Point for Render ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns this
    app.run(host="0.0.0.0", port=port)


