import os
import io
import time
import uuid
import base64
import requests
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
from google import genai  # ✅ Correct import for Google GenAI SDK (from your working example)
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    JWTManager,
    verify_jwt_in_request
)
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import ExpiredSignatureError
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# ------------------------
# ✅ Helper for optional JWT
# ------------------------
def get_jwt_identity_optional():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except (NoAuthorizationError, ExpiredSignatureError):
        return None

# ------------------------
# ✅ Flask App Setup
# ------------------------
app = Flask(__name__)
CORS(app)

# --- App Configuration ---
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback_secret_key_123")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///site.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "fallback_jwt_secret_456")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)

# --- [MERGED] Folder Configuration (from Image App) ---
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
app.config['GENERATED_FOLDER'] = os.path.abspath(GENERATED_FOLDER)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

print(f"[INFO] Upload folder: {app.config['UPLOAD_FOLDER']}")
print(f"[INFO] Generated folder: {app.config['GENERATED_FOLDER']}")

# ------------------------
# ✅ [MERGED] Google API Configuration
# ------------------------
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") #'AIzaSyAEGRhQSYTSCaTlm0_Ep-37OQAUd_-4R4M'os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("[FATAL ERROR] GOOGLE_API_KEY is not set. Please add it in Render Environment Variables.")

# --- 1. Client for Text Generation (from your working app) ---
try:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    print("[INFO] Google GenAI SDK (for Text) initialized.")
except Exception as e:
    print(f"[ERROR] Failed to initialize Google GenAI client: {e}")
    client = None

# --- 2. REST API URL for Image Generation (from your original app) ---
MODEL_NAME = "gemini-2.5-flash-image"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
print(f"[INFO] Image API (REST) endpoint set for model: {MODEL_NAME}")


# ------------------------
# ✅ Database Setup
# ------------------------
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# ------------------------
# ✅ [MERGED] Style Prompts (from your original app)
# ------------------------
STYLE_PROMPTS = {
    # The "Restore" prompt, now heavily detailed and restrictive
    "restore": {
        "artist_style": "a world-class forensic photo restoration specialist and lead digital conservator",
        "style_description": (
            "This is a professional, high-fidelity restoration job, NOT an artistic recreation. "
            "Your primary goal is to enhance and repair the original image to its pristine state. "
            "ABSOLUTELY NO artistic changes are permitted. DO NOT alter the subject's original face, features, "
            "pose, clothing, body shape, or physical attributes. DO NOT add, remove, or change objects in the background. "
            "Your tasks are strictly technical: Meticulously remove all visual artifacts, including scratches, "
            "dust, creases, tears, water stains, and severe film grain. Correct severe color casts, "
            "restore faded, washed-out colors to their original vibrancy, and perfectly balance the histogram. "
            "Recover all clipped highlights and crushed shadows to reveal lost detail. "
            "Finally, intelligently sharpen the entire image to a modern 4K or 8K clarity, as if it were a new digital scan "
            "from the original, undamaged film negative. The final image must be a perfect, clean master of the original photo."
        )
    },
    
    # All other prompts, expanded for powerful control
    "cinematic": {
        "artist_style": "an award-winning cinematic director and Director of Photography, in the style of Roger Deakins or Denis Villeneuve",
        "style_description": (
            "A breathtaking 16:9 anamorphic film still, captured on a Panavision lens with subtle, realistic lens flare. "
            "Features professional 8K resolution, volumetric 'god ray' lighting cutting through a hazy, atmospheric scene. "
            "Apply a sophisticated cinematic color grade (moody teal-orange or desaturated noir). "
            "The composition must be meticulous, with deep, rich shadows, perfectly controlled highlights, and a light, realistic film grain "
            "to simulate an Arri Alexa 65 camera sensor."
        )
    },
    "portrait": {
        "artist_style": "a world-class editorial portrait photographer, referencing Annie Leibovitz, shooting for a 'Vogue' or 'Vanity Fair' cover",
        "style_description": (
            "An ultra-sharp 8K medium-shot studio portrait, captured with a high-end 85mm f/1.2 prime lens. "
            "Features exceptionally creamy, buttery bokeh and perfect, distinct catchlights in the subject's eyes. "
            "The lighting is a flawless, flattering softbox setup (like a large octabox) for the key light, with a subtle fill "
            "from a V-flat to gently lift the shadows. Set against a pristine, minimalist seamless paper background in a neutral grey or pure white. "
            "Includes subtle, professional-grade skin retouching for a perfect, but natural, finish."
        )
    },
    "anime": {
        "artist_style": "a lead key animator and art director from a high-budget feature film studio, like MAPPA, Ufotable, or CoMix Wave Films",
        "style_description": (
            "A 'sakuga'-quality, high-budget modern anime style, suitable for a blockbuster theatrical release. "
            "Features a hyper-dynamic composition with crisp, complex, cel-shaded line art and advanced digital compositing. "
            "The scene is packed with effects: volumetric lighting from the environment, glowing magical particle effects, "
            "and cinematic lens flares. The character must have highly expressive, intricately detailed eyes. "
            "The background must be a painterly, highly detailed cinematic matte painting, not a simple gradient."
        )
    },
    "fantasy": {
        "artist_style": "a legendary fantasy illustrator and senior concept artist, blending the styles of Frank Frazetta and 'Elden Ring' art direction",
        "style_description": (
            "An epic, painterly, and hyper-detailed fantasy portrait with dynamic, visible brushstrokes. "
            "The subject is captured in a dynamic, heroic pose, adorned with intricate, battle-worn, glowing armor and mythical artifacts. "
            "The scene is lit with dramatic chiaroscuro and powerful volumetric god-rays, which illuminate swirling "
            "magical particle effects and atmospheric fog. The background is a vast, mythical landscape with "
            "a strong sense of atmospheric perspective and epic scale."
        )
    },
    "realistic": {
        "artist_style": "a master of hyperrealistic technical photography, using a Phase One medium format 150MP camera system",
        "style_description": (
            "An 8K, hyperrealistic photograph, absolutely indistinguishable from reality. "
            "Shot with a macro-level prime lens to capture every single pore, fiber, and skin texture with flawless, critical "
            "edge-to-edge sharpness. Lit with flawless, clinical, and perfectly color-balanced (5600K) studio lighting. "
            "Must have perfect color rendition, zero digital noise, zero film grain, and absolutely no artistic filters. "
            "The final output must be pure, sharp, unadulterated reality."
        )
    },
    "vintage": {
        "artist_style": "a master 1950s photojournalist using a classic Rolleiflex or Leica M3 camera",
        "style_description": (
            "An authentic 1950s vintage photograph, perfectly simulating aged Kodachrome or Agfa film stock. "
            "Features a beautifully desaturated, slightly warm, sepia-toned color palette with faded colors. "
            "The image must have heavy but natural-looking film grain, soft focus (not motion blur), and "
            "authentic optical imperfections like vignetting and subtle, accidental light leaks. "
            "Lighting should appear to be from a single, on-camera harsh flashbulb, creating distinct, hard shadows."
        )
    },
    "dreamy": {
        "artist_style": "an ethereal and dreamy aesthetic photographer, master of soft-focus and 'bloom' lighting",
        "style_description": (
            "A surreal, dreamlike portrait defined by an angelic, glowing 'bloom' effect. "
            "Features extremely soft, diffused lighting, as if shot through a heavy mist filter or Vaseline on the lens. "
            "Highlights are intentionally overexposed, glowing, and bleeding into the midtones. "
            "The color palette is restricted to soft pastels and heavily desaturated tones. "
            "The scene is filled with a gentle, hazy fog and noticeable chromatic aberration for a surreal, otherworldly, and magical feel."
        )
    },
    "moody": {
        "artist_style": "a moody, atmospheric film noir director, mastering low-key and expressive Rembrandt lighting",
        "style_description": (
            "A dark, emotional, and highly atmospheric studio portrait in a classic film noir style. "
            "Lit with dramatic low-key or Rembrandt lighting (a single, hard, directional source) to create "
            "intense chiaroscuro—a battle between deep, crushed black shadows and stark, bright highlights. "
            "The image is heavily desaturated, high-contrast, and evokes a palpable, somber, and deeply cinematic atmosphere. "
            "Focus on the texture and form revealed by the single light source."
        )
    },
    "neon": {
        "artist_style": "a high-fashion cyberpunk and neon-noir photographer, shooting a 'Blade Runner' themed editorial for 'Dazed' magazine",
        "style_description": (
            "A high-fashion studio shoot, lit *only* by vibrant, saturated, and flickering neon lights. "
            "The aesthetic is pure cyberpunk-noir, with a dominant pink, cyan, and purple color palette. "
            "Features wet, reflective surfaces (like a rain-slicked floor) that mirror the lights. "
            "The subject's skin and high-fashion clothing must be catching the glowing, colored highlights. "
            "Use deep shadows and include anamorphic lens flares from the neon tubes."
        )
    },
    "default": {
        "artist_style": "a high-end commercial and e-commerce studio photographer, focused on flawless, clean results for a major brand",
        "style_description": (
            "A flawless, high-end commercial studio portrait, perfect for an advertisement or product catalog. "
            "Lit with a perfect, even, shadowless 3-point lighting setup (large softbox key, fill light, and subtle rim light). "
            "Set against a perfectly clean, 50% neutral grey seamless paper backdrop. "
            "The image must be 8K, ultra-high resolution, with crystal-clear, edge-to-edge focus and perfectly balanced, "
            "true-to-life colors. Must be commercially viable, pristine, and look professionally retouched."
        )
    }
}


# ------------------------
# ✅ Database Models
# ------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    searches = db.relationship('SearchHistory', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.email}')"


class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    prompt_content = db.Column(db.Text, nullable=False)
    generated_result = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"SearchHistory('{self.title}', User: {self.user_id})"

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'prompt_content': self.prompt_content,
            'generated_result': self.generated_result,
            'timestamp': self.timestamp.isoformat()
        }


# ------------------------
# ✅ JWT Config
# ------------------------
@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)


# ------------------------
# ✅ Home Route
# ------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "✅ CreatorsAI API (Merged Image & Text) is live!"})


# ------------------------
# ✅ Hashtag Generator Route
# ------------------------
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    post_content = data.get("post", "")
    if not post_content:
        return jsonify({"error": "No post content provided"}), 400

    prompt = f"""
    You are an expert social media strategist.
    The user provided this post caption: "{post_content}"
    Your task:
    1. Keep the user's caption exactly as it is.
    2. Add a new line and generate ONLY 7–10 trending, SEO-optimized hashtags.
    3. Make hashtags aesthetic and relevant.
    Format:
    [Original caption]

    [Hashtags]
    """

    try:
        if not client:
             return jsonify({"error": "Google AI client not initialized. Check API Key."}), 500
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Using model from your working example
            contents=prompt
        )
        result = response.text.strip() if hasattr(response, "text") else "No response text received."
        return jsonify({"result": result})
    except Exception as e:
        print(f"[ERROR] /generate: {e}")
        return jsonify({"error": str(e)}), 500


# ------------------------
# ✅ Chat Response Route
# ------------------------
@app.route("/respond", methods=["POST"])
def respond():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    prompt_content = data.get("prompt", "")
    if not prompt_content:
        return jsonify({"error": "No prompt content provided"}), 400

    chat_prompt = f"""
    You are CreatorsAI — a friendly, insightful assistant for the creator economy.
    A user asked:
    "{prompt_content}"

    Give a concise, practical answer tailored for content creators.
    """

    try:
        if not client:
             return jsonify({"error": "Google AI client not initialized. Check API Key."}), 500
        
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Using model from your working example
            contents=chat_prompt
        )
        result = response.text.strip() if hasattr(response, "text") else "No response text received."
        return jsonify({"result": result})
    except Exception as e:
        print(f"[ERROR] /respond: {e}")
        return jsonify({"error": str(e)}), 500


# ------------------------
# ✅ Auth Routes
# ------------------------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=hashed)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=user)
    return jsonify(access_token=token), 200


# ------------------------
# ✅ User History Routes
# ------------------------
@app.route("/api/history", methods=["POST"])
@jwt_required()
def save_history():
    user_id = get_jwt_identity()
    data = request.get_json()
    prompt = data.get("prompt")
    result = data.get("result")

    if not prompt or not result:
        return jsonify({"error": "Prompt and result required"}), 400

    title = (prompt[:40] + "...") if len(prompt) > 40 else prompt
    new_item = SearchHistory(title=title, prompt_content=prompt, generated_result=result, user_id=user_id)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({"message": "History saved", "history_id": new_item.id}), 201


@app.route("/api/history", methods=["GET"])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    items = SearchHistory.query.filter_by(user_id=user_id).order_by(SearchHistory.timestamp.desc()).all()
    return jsonify([item.to_dict() for item in items]), 200


# ---------------------------------------------
# ✅ [NEW/MERGED] IMAGE GENERATION ROUTES
# ---------------------------------------------

@app.route('/upload-reference', methods=['POST'])
def upload_reference():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400

        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        print(f"[INFO] Reference uploaded: {filename}")
        return jsonify({
            "message": "File uploaded successfully",
            "filename": filename,
            "url": f"/uploads/{filename}" # Note: This URL is relative to the backend
        }), 200

    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        style_key = data.get("style", "default")
        ref_filename = data.get("reference_filename")

        if not ref_filename:
            return jsonify({"error": "Reference filename missing"}), 400

        style = STYLE_PROMPTS.get(style_key, STYLE_PROMPTS["default"])
        ref_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(ref_filename))

        if not os.path.exists(ref_path):
            return jsonify({"error": "Reference image not found"}), 404

        print(f"[INFO] Generating image in '{style_key}' style using {ref_filename}")

        # Convert image to base64
        with Image.open(ref_path) as img:
            buffer = io.BytesIO()
            img.convert("RGB").save(buffer, format="JPEG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Create Gemini request payload
        prompt = (
            f"You are a {style['artist_style']}.\n"
            f"Recreate the person in {style['style_description']}.\n"
            "Maintain the same face, gender, and posture."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                ]
            }],
            "generationConfig": {"temperature": 0.7, "topP": 0.9},
        }

        headers = {"Content-Type": "application/json"}
        # Using the API_URL defined at the top, which uses requests, not the SDK
        response = requests.post(API_URL, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            print(f"[ERROR] Gemini API Error: {response.text}")
            return jsonify({"error": f"Gemini API returned {response.status_code}", "details": response.text}), response.status_code

        result = response.json()
        
        if "promptFeedback" in result:
             print(f"[WARN] Gemini returned promptFeedback: {result['promptFeedback']}")
             block_reason = result.get("promptFeedback", {}).get("blockReason", "Unknown")
             return jsonify({"error": f"Generation failed due to safety settings: {block_reason}"}), 400

        candidates = result.get("candidates", [])
        if not candidates:
            print("[WARN] Gemini returned no candidates.")
            return jsonify({"error": "No output from Gemini"}), 400

        parts = candidates[0].get("content", {}).get("parts", [])
        gen_b64 = None
        for part in parts:
            if "inline_data" in part:
                gen_b64 = part["inline_data"]["data"]
                break
            elif "inlineData" in part: # Handle camelCase variation
                gen_b64 = part["inlineData"]["data"]
                break

        if not gen_b64:
            print("[WARN] Gemini returned no image data.")
            return jsonify({"error": "Gemini returned no image data"}), 400

        # Save generated image
        generated_filename = f"gen_{int(time.time())}_{style_key}.jpg"
        generated_path = os.path.join(app.config['GENERATED_FOLDER'], generated_filename)
        with open(generated_path, "wb") as f:
            f.write(base64.b64decode(gen_b64))

        print(f"[INFO] Generation complete: {generated_filename}")
        return jsonify({
            "message": "Image generated successfully",
            "generated_image_url": f"/generated/{generated_filename}" # Relative to backend
        }), 200

    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
        return jsonify({"error": str(e)}), 500

# ------------------------------------------------------
# 🗂 [NEW/MERGED] Serve Uploaded and Generated Files
# ------------------------------------------------------
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generated/<path:filename>')
def serve_generated(filename):
    return send_from_directory(app.config['GENERATED_FOLDER'], filename)


# ------------------------
# ✅ Server Runner for Render
# ------------------------
if __name__ == "__main__":
    with app.app_context():
        print("Checking/creating database tables...")
        db.create_all()
        print("Database ready.")
    port = int(os.environ.get("PORT", 5000))
    # Note: app.run() is fine for Render's environment, but gunicorn is preferred.
    # Since your working example uses this, we will keep it.
    app.run(host="0.0.0.0", port=port)

