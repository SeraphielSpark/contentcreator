import os
import io
import time
import uuid
import base64
import requests
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_jwt_extended import verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import ExpiredSignatureError
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import google.genai as genai

# ======================================================
# ⚙️ CORE APP, DB, & AUTH SETUP
# ======================================================

app = Flask(__name__)

# --- CORS Configuration ---
# Allow all origins for now. 
# For production, restrict this to your frontend's URL:
# CORS(app, origins=["http://your-frontend-domain.com"], supports_credentials=True)
CORS(app)

# --- App Configuration ---
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a_very_strong_fallback_secret_key_123")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///site.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "a_super_secret_jwt_key_456")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)

# --- Folder Configuration (from Image App) ---
# WARNING: These are EPHEMERAL on Render. Use cloud storage or Render Disks for production.
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
app.config['GENERATED_FOLDER'] = os.path.abspath(GENERATED_FOLDER)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

print(f"[INFO] Upload folder: {app.config['UPLOAD_FOLDER']}")
print(f"[INFO] Generated folder: {app.config['GENERATED_FOLDER']}")

# --- Initialize Extensions ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


# ======================================================
# 🔑 UNIFIED GOOGLE API CONFIGURATION
# ======================================================

# --- Central API Key ---
# IMPORTANT: This is hardcoded. For production, set this as an
# environment variable on Render (GOOGLE_API_KEY) and use:
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("[FATAL ERROR] GOOGLE_API_KEY environment variable not set. API calls will fail.")

# --- 1. GenAI SDK (for Text Generation) ---
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("[INFO] Google GenAI SDK (for Text) configured.")
except Exception as e:
    print(f"[ERROR] Failed to configure Google GenAI SDK: {e}")

# --- 2. Image API Endpoint (for Image Generation) ---
# This uses the v1beta REST API, which is different from the SDK
MODEL_NAME = "gemini-2.5-flash-image-preview"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
print(f"[INFO] Google Image API (for Images) endpoint set for model: {MODEL_NAME}")


# ======================================================
# 🎨 STYLE PRESETS (from Image App)
# ======================================================
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

# ======================================================
# 🗃️ DATABASE MODELS (from Auth App)
# ======================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    searches = db.relationship('SearchHistory', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.email}')"

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False) # Title for the sidebar
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

# ======================================================
# 🔐 JWT & AUTH ROUTES (from Auth App)
# ======================================================

@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "✅ CreatorsAI API (Merged Image & Text) is live!"})

@app.route("/auth/register", methods=["POST"])
def register():
    print("\n--- Request received at /auth/register ---")
    data = request.get_json()
    if not data: return jsonify({"error": "Request must be JSON"}), 400
    email = data.get("email")
    password = data.get("password")
    print(f"[DEBUG] /register: Attempting registration for email: {email}")
    if not email or not password: return jsonify({"error": "Email and password are required"}), 400
    user_exists = User.query.filter_by(email=email).first()
    if user_exists:
        print(f"[WARN] /register: Email already exists: {email}")
        return jsonify({"error": "Email already exists"}), 409
    try:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        print(f"[INFO] /register: User created successfully: {email}")
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] /register: Database error: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/auth/login", methods=["POST"])
def login():
    print("\n--- Request received at /auth/login ---")
    data = request.get_json()
    if not data: return jsonify({"error": "Request must be JSON"}), 400
    email = data.get("email")
    password = data.get("password")
    print(f"[DEBUG] /login: Attempting login for email: {email}")
    if not email or not password: return jsonify({"error": "Email and password are required"}), 400
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=user)
        print(f"[INFO] /login: Login successful for: {email}")
        return jsonify(access_token=access_token), 200
    else:
        print(f"[WARN] /login: Invalid credentials for: {email}")
        return jsonify({"error": "Invalid credentials"}), 401


# ======================================================
# 🖼️ IMAGE GENERATION ROUTES (from Image App)
# ======================================================

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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            print(f"[ERROR] Gemini API Error: {response.text}")
            return jsonify({"error": f"Gemini API returned {response.status_code}"}), response.status_code

        result = response.json()
        
        # Handle potential "promptFeedback" block indicating a safety/block issue
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
# 🗂 Serve Uploaded and Generated Files
# ------------------------------------------------------
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generated/<path:filename>')
def serve_generated(filename):
    return send_from_directory(app.config['GENERATED_FOLDER'], filename)


# ======================================================
# 💬 TEXT GENERATION ROUTES (from Auth App)
# ======================================================

@app.route("/generate", methods=["POST"])
def generate():
    print("\n--- Request received at /generate ---")
    data = request.get_json()
    if not data:
        print("[ERROR] /generate: No JSON data received")
        return jsonify({"error": "Request must be JSON"}), 400

    post_content = data.get("post", "")
    print(f"[DEBUG] /generate: Received post content: {post_content[:100]}...")

    if not post_content:
        print("[ERROR] /generate: No 'post' content in JSON")
        return jsonify({"error": "No post content provided"}), 400

    prompt = f"""
    You are an expert social media strategist.
    The user provided this post caption: "{post_content}"
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
        print("[DEBUG] /generate: Calling Google GenAI SDK...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        result = response.text.strip()

        print(f"[DEBUG] /generate: Responding with result: {result[:100]}...")
        return jsonify({"result": result})

    except Exception as e:
        print(f"[ERROR] /generate: Exception occurred: {str(e)}")
        if "API_KEY" in str(e) or "PERMISSION_DENIED" in str(e):
            print("[ERROR] /generate: Google API Key error.")
            return jsonify({"error": "Invalid or missing Google API Key. Check server logs."}), 500
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500


@app.route("/respond", methods=["POST"])
def respond():
    print("\n--- Request received at /respond ---")
    data = request.get_json()
    if not data:
        print("[ERROR] /respond: No JSON data received")
        return jsonify({"error": "Request must be JSON"}), 400

    prompt_content = data.get("prompt", "")
    print(f"[DEBUG] /respond: Received prompt: {prompt_content[:100]}...")

    if not prompt_content:
        print("[ERROR] /respond: No 'prompt' content in JSON")
        return jsonify({"error": "No prompt content provided"}), 400

    chat_prompt = f"""
    You are CreatorsAI, a helpful and intelligent assistant for the creator economy.
    A user has asked:
    "{prompt_content}"

    Provide a helpful, concise, and relevant response tailored to content creators.
    """

    try:
        # Note: Your original code used a different SDK call. 
        # This is the standard v1.5 call, matching the /generate route.
        print("[DEBUG] /respond: Calling Google GenAI SDK...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(chat_prompt)
        result = response.text.strip()
        
        print(f"[DEBUG] /respond: GenAI response received: {result[:100]}...")
        return jsonify({"result": result})

    except Exception as e:
        print(f"[ERROR] /respond: Exception occurred: {str(e)}")
        if "API_KEY" in str(e) or "PERMISSION_DENIED" in str(e):
            print("[ERROR] /respond: Google API Key error.")
            return jsonify({"error": "Invalid or missing Google API Key. Check server logs."}), 500
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

# ======================================================
# 📚 HISTORY ROUTES (from Auth App)
# ======================================================

@app.route("/api/history", methods=["POST"])
@jwt_required()
def save_history():
    print("\n--- Request received at POST /api/history ---")
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user: return jsonify({"error": "User not found"}), 404
    print(f"[DEBUG] POST /history: User: {user.email}")
    data = request.get_json()
    if not data: return jsonify({"error": "Request must be JSON"}), 400
    prompt = data.get("prompt")
    result = data.get("result")
    if not prompt or not result: return jsonify({"error": "Prompt and result are required"}), 400
    title = (prompt[:40] + '...') if len(prompt) > 40 else prompt
    try:
        search = SearchHistory(title=title, prompt_content=prompt, generated_result=result, author=user)
        db.session.add(search)
        db.session.commit()
        print(f"[INFO] POST /history: History saved for user {user.email}")
        return jsonify({"message": "History saved", "history_id": search.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] POST /history: Database error: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/history", methods=["GET"])
@jwt_required()
def get_history():
    print("\n--- Request received at GET /api/history ---")
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user: return jsonify({"error": "User not found"}), 404
    print(f"[DEBUG] GET /history: Fetching history for user: {user.email}")
    try:
        searches = SearchHistory.query.filter_by(user_id=user.id).order_by(SearchHistory.timestamp.desc()).all()
        print(f"[DEBUG] GET /history: Found {len(searches)} history items.")
        return jsonify([search.to_dict() for search in searches]), 200
    except Exception as e:
        print(f"[ERROR] GET /history: Database error: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route("/api/history/<int:history_id>", methods=["GET"])
@jwt_required()
def get_single_history_item(history_id):
    print(f"\n--- Request received at GET /api/history/{history_id} ---")
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user: return jsonify({"error": "User not found"}), 404
    print(f"[DEBUG] GET /history/{history_id}: User: {user.email}")
    try:
        search = SearchHistory.query.filter_by(id=history_id, user_id=current_user_id).first()
        if not search:
            print(f"[WARN] GET /history/{history_id}: History item not found or not authorized for user {user.email}")
            return jsonify({"error": "History not found or not authorized"}), 404
        print(f"[DEBUG] GET /history/{history_id}: Found history item.")
        return jsonify(search.to_dict()), 200
    except Exception as e:
        print(f"[ERROR] GET /history/{history_id}: Database error: {str(e)}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

# ======================================================
# ▶️ RUN SERVER
# ======================================================
if __name__ == "__main__":
    with app.app_context():
        print("Creating database tables if they don't exist...")
        try:
            db.create_all()
            print("Database tables checked/created.")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    # Port for Render (uses $PORT) or defaults to 5000 for local
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask app on host 0.0.0.0, port {port}")
    app.run(host="0.0.0.0", port=port, debug=False) # Debug=False is better for production
