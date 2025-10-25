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

        # --- [FIX] Safely access the response text ---
        try:
            # The 'response.text' accessor will raise a ValueError if content is blocked.
            # We can catch this specific error.
            hashtags_text = response.text.strip()
        except ValueError:
            # This happens if the response was blocked by safety filters
            print("Content generation failed, likely due to safety filters.")
            print("Prompt Feedback:", response.prompt_feedback)
            return jsonify({"error": "Content generation failed. The prompt or response was blocked by safety filters."}), 500
        except Exception as e:
            # Catch other potential issues with the response object
            print(f"Error accessing response text: {e}")
            return jsonify({"error": f"Error processing model response: {e}"}), 500


        # --- Return in the *exact same* format as the original Cohere API ---
        return jsonify({"generations": [{"text": hashtags_text}]})

    except Exception as e:
        # This outer block catches errors in request parsing or the model.generate_content() call itself
        print(f"Error during /ask route: {e}")
        return jsonify({"error": str(e)}), 500


# --- Entry Point for Render ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render auto-assigns this
    app.run(host="0.0.0.0", port=port)


