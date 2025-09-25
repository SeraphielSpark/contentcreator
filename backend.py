import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai

# --- config -------------------------------------------------------
API_KEY = "AIzaSyC5OqbLCKuL-uncdxxe7x81t8g9ttE3J_c"

client = genai.Client(api_key=API_KEY)
app = Flask(__name__)
CORS(app)  # GLOBAL, before routes

# --- route --------------------------------------------------------
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify(error="Content required"), 400

    prompt = f'Extract 10 SEO hashtags from: "{content}"\nReturn only tags, comma-separated.'
    try:
        rsp = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        text = rsp.text.strip() if rsp.text else ""
    except Exception as e:
        print("Gemini error:", e)
        return jsonify(error="Gen failed"), 500

    hashtags = [t.strip() for t in text.split(",") if t.strip().startswith("#")]
    return jsonify(hashtags=hashtags)

# --- health-check (helps Render verify deploy) --------------------
@app.route("/")
def ok():
    return "ok", 200
