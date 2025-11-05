import os
import io
import time
import uuid
import base64
import requests
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory
# Note: Ensure 'google.genai' is updated in your requirements.txt
# (as 'google-generativeai') to fix the 'no attribute configure' error.
from google import genai 
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    JWTManager,
    verify_jwt_in_request,
    get_current_user
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

# Updated CORS setup
CORS(app,
     resources={r"/*": {"origins": ["*"]}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Authorization", "Content-Type"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# --- App Configuration ---
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback_secret_key_123")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)
app.config["JWT_SECRET_KEY"] = "super-secret-key"

# --- Folder Configuration ---
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
app.config['GENERATED_FOLDER'] = os.path.abspath(GENERATED_FOLDER)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

print(f"[INFO] Upload folder: {app.config['UPLOAD_FOLDER']}")
print(f"[INFO] Generated folder: {app.config['GENERATED_FOLDER']}")

# --- Database Path ---
# Using /tmp for compatibility with read-only filesystems like Render
db_path = os.path.join("/tmp", "app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
print(f"[INFO] Database path: {app.config['SQLALCHEMY_DATABASE_URI']}")


# ------------------------
# ✅ Google API Configuration
# ------------------------
# [MODIFIED] Using updated environment variable name
#GOOGLE_API_KEY1 = os.environ.get("GEMINI")
API_KEY = os.environ.get("GEMINI")
client = genai.Client(api_key=API_KEY)
# --- 2. REST API URL for Image Generation ---
MODEL_NAME = "gemini-2.5-flash-image" 
# [MODIFIED] Using updated environment variable name
if not API_KEY:
    print("[FATAL ERROR] GEMINI (for Image API) is not set.")

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
print(f"[INFO] Image API (REST) endpoint set for model: {MODEL_NAME}")


# ------------------------
# ✅ Database Setup
# ------------------------

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# ✅✅✅ --- FIX --- ✅✅✅
# Initialize SQLAlchemy *after* app config is set
db = SQLAlchemy(app)
# ✅✅✅ ----------- ✅✅✅


# ------------------------
# ✅ [MERGED] Style Prompts (Keeping for legacy/reference)
# ------------------------
STYLE_PROMPTS = {
    # ... (Your "restore", "cinematic", "portrait", etc. prompts are all still here) ...
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
            "The scene is lit with dramatic chiaroscurp and powerful volumetric god-rays, which illuminate swirling "
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
    },
    "spooky": {
    "artist_style": "a world-class cinematic horror photographer and visual effects director specializing in realistic Halloween imagery",
    "style_description": (
        "A hyper-realistic, cinematic Halloween portrait that transforms the subject into a spooky, haunting, yet believable character. "
        "Change the subject’s clothing, background, and environment to fully match a Halloween theme (such as witch, vampire, ghost, pumpkin queen, or dark angel), "
        "but DO NOT alter or distort the subject’s original face, features, or expression — their identity must remain perfectly recognizable. "
        "Apply detailed, eerie atmospheric lighting (moonlight, fog, candle glow, or flickering shadows) with realistic volumetric effects. "
        "Use ultra-sharp 8K resolution, professional-grade color grading, and meticulous texture enhancement. "
        "Backgrounds must be immersive and cinematic — haunted mansions, graveyards, forests, or gothic interiors — all with a photographic level of realism. "
        "Include subtle motion in hair or clothing for dynamic presence. "
        "Final output should look like a real Halloween photoshoot captured with a Canon R5 or Arri Alexa camera under dramatic studio lighting. "
        "Deliver a perfect balance between spooky atmosphere and beautiful realism, ensuring it feels like a luxury Halloween editorial portrait, not a cartoon."
    )
},
}


# ------------------------
# ✅ Database Models
# ------------------------
# These models are now defined *after* db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)    
    searches = db.relationship('SearchHistory', backref='author', lazy=True)
    
    # --- Fields for Credit System ---
    plan = db.Column(db.String(100), nullable=False, default='free') # e.g., 'free', 'standard'
    credits = db.Column(db.Integer, nullable=False, default=200) # Start new users with 200 credits
    
    def __repr__(self):
        # [MODIFIED] Updated to show credits
        return f"User('{self.username}', Plan: '{self.plan}', Credits: {self.credits})"


class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    prompt_content = db.Column(db.Text, nullable=False)
    generated_result = db.Column(db.Text, nullable=False) # This will store the /generated/ URL
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
# ✅ Create Tables
# ------------------------
# ✅✅✅ --- FIX --- ✅✅✅
# This is moved to *after* the models (User, SearchHistory) are defined.
with app.app_context():
    print("[INFO] Initializing database tables...")
    db.create_all()
    print("[INFO] Database tables initialized.")
# ✅✅✅ ----------- ✅✅✅


# ------------------------
# ✅ JWT Config
# ------------------------

# --- [FIXED] This function has been REMOVED (as in your original) ---
# @jwt.user_identity_loader
# ...

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    try:
        # This will now work because User model is defined
        return User.query.get(int(identity))
    except (ValueError, TypeError):
        return None

# This variable 'number' doesn't seem to be used anywhere.
# It's harmless, but you could remove it.
number = '' 

@app.before_request
def preserve_authorization_header():
    if "Authorization" not in request.headers and "HTTP_AUTHORIZATION" in request.environ:
        request.headers = dict(request.headers)
        request.headers["Authorization"] = request.environ["HTTP_AUTHORIZATION"]

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
    data = request.get_json(silent=True) or {}
    
    # --- [FIX 1] ---
    # Look for "post" to match your frontend
    content = (data.get("post") or "").strip() 
    # --- [END FIX 1] ---
    
    if not content:
        return jsonify(error="Content required (must be sent as 'post')"), 400

    # --- [FIX 2] ---
    # Separated prompts for the new client method
    system_prompt = (
        "You are an expert social media strategist.\n"
        "Your task is to extract exactly 7 SEO-optimized hashtags from the user's content.\n"
        "RULES:\n"
        "1. Return ONLY the hashtags.\n"
        "2. Each hashtag must start with a #.\n"
        "3. Separate each hashtag with a comma.\n"
        "4. Do not include any other text, titles, or explanations."
    )
    user_prompt = f"Here is the content: \"{content}\""
    # --- [END FIX 2] ---

    try:
        # --- [FIX 3] ---
        # Use the correct model name and the new config
        rsp = client.models.generate_content(
            model="gemini-2.5-flash",  # <-- Correct model
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            ),
            contents=user_prompt
        )
        # --- [END FIX 3] ---
        
        text = rsp.text.strip() if rsp.text else ""

    except Exception as e:
        print("Gemini error:", e)
        # Pass the Google error to the frontend
        return jsonify(error=f"Gen failed: {str(e)}"), 500

    # This parsing logic is good and now matches the prompt
    hashtags = [t.strip() for t in text.split(",") if t.strip().startswith("#")]
    
    if not hashtags:
        # Handle cases where the model didn't return what we want
        print(f"Model returned unexpected text: {text}")
        return jsonify(error="Failed to parse hashtags from model response", model_output=text), 500

    return jsonify(hashtags=hashtags)
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
        response = client.models.generate_content(model="gemini-2.5-flash", contents=chat_prompt)
        result = response.text.strip() if rsp.text else ""
        return jsonify({"result": result})
    except Exception as e:
        print(f"[ERROR] /respond: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Register endpoint
# ----------------------------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = data.get("email")
    password = data.get("password")

    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "User already exists"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    new_user = User(
        username=username,
        password=hashed_password,
        plan="free",
        credits=200
    )
    db.session.add(new_user)
    db.session.commit()

    token = create_access_token(identity=str(new_user.id))
    return jsonify({
        "token": token,
        "user_id": new_user.id,
        "username": username
    }), 201


# ----------------------------
# Login endpoint
# ----------------------------
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"msg": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id))
    print(f"[INFO] Login successful for: {user.username} (Credits: {user.credits})")
    
    # Create user info object *before* closing session
    user_info = {       
        "id": user.id,
        "email": user.username,
        "plan": user.plan,
        "credits": user.credits, # Send the actual current credits
        "point": user.credits,   # 'point' seems redundant, but keeping your structure
        'access_token': token
    }
    
    db.session.close() # Good practice
    
    print(f"[INFO] Returning user info: {user_info}")
    return jsonify(user_info), 200


# ------------------------
# ✅ User History Routes
# ------------------------
@app.route("/api/history", methods=["POST"])
@jwt_required()
def save_history():
    user_id = get_jwt_identity()
    data = request.get_json()
    # [MODIFIED] Get the full prompt from the request
    prompt = data.get("prompt") # This will be the full prompt string
    result = data.get("result") # This is the generated_url
    title = data.get("title")   # Get the simple title (e.g., "LinkedIn Classic")

    if not prompt or not result or not title:
        return jsonify({"error": "Title, prompt, and result required"}), 400
    
    new_item = SearchHistory(
        title=title, 
        prompt_content=prompt, # Save the full detailed prompt
        generated_result=result,
        user_id=user_id
    )
    db.session.add(new_item)
    db.session.commit()
    db.session.close()
    return jsonify({"message": "History saved", "history_id": new_item.id}), 201


@app.route("/api/history", methods=["GET"])
@jwt_required()
def get_history():
    user_id = get_jwt_identity()
    items = SearchHistory.query.filter_by(user_id=user_id).order_by(SearchHistory.timestamp.desc()).all()
    db.session.close()
    return jsonify([item.to_dict() for item in items]), 200


# ---------------------------------------------
# ✅ IMAGE GENERATION ROUTES
# ---------------------------------------------

@app.route('/upload-reference', methods=['POST'])
@jwt_required(optional=True) # Allows upload even if not logged in
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
            "url": f"/uploads/{filename}"
        }), 200

    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/generate-image', methods=['POST'])
@jwt_required()
def generate_image():
    IMAGE_COST = 10
    current_user = get_current_user() # This works thanks to user_lookup_loader

    if current_user.credits < IMAGE_COST:
        print(f"[LIMIT] User {current_user.username} (Credits: {current_user.credits}) needs {IMAGE_COST}.")
        return jsonify({"error": "Not enough credits"}), 403

    try:
        data = request.json
        # [MODIFIED] Get all new fields from frontend
        ref_filename = data.get("reference_filename")
        category = data.get("category")
        theme = data.get("theme")
        look = data.get("look")
        color_tone = data.get("color_tone")
        usage = data.get("usage")
        custom_prompt = data.get("custom_prompt") # This can be None

        # [MODIFIED] Validate new fields
        if not ref_filename:
            return jsonify({"error": "Reference filename missing"}), 400
        if not category:
            return jsonify({"error": "Category missing"}), 400
        if not theme:
            return jsonify({"error": "Theme missing"}), 400

        # [MODIFIED] Use a generic artist, as style is now dynamic
        artist = "a world-class digital artist and photo-manipulation expert"

        ref_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(ref_filename))
        if not os.path.exists(ref_path):
            return jsonify({"error": "Reference image not found"}), 404

        print(f"[INFO] User {current_user.username} generating image. Theme: '{theme}', Look: '{look}'")

        # Convert image to base64 safely
        with Image.open(ref_path) as img:
            buffer = io.BytesIO()
            img.thumbnail((1024, 1024)) # Resize to prevent overly large payloads
            img.convert("RGB").save(buffer, format="JPEG", quality=90)
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        # [MODIFIED] Create the new dynamic prompt
        prompt = (
            f"You are {artist}.\n"
            f"Your task is to transform the person in the reference photo according to the user's request. "
            f"**The most important rule is to strictly maintain their exact face, features, expression, and identity. DO NOT change their face.**\n\n"
            f"--- Main Category ---\n"
            f"The desired category is: **{category}**.\n\n"
            f"--- Main Theme ---\n"
            f"The desired theme is: **{theme}**. This means you must change the clothing, background, and overall atmosphere to match this theme. For example, if the theme is 'LinkedIn Classic', give them professional attire and a clean, neutral background. If 'Epic Knight', give them armor and a fantasy background.\n\n"
            f"--- Desired Look ---\n"
            f"The final image must have a **{look}** look. If 'artistic' or 'cinematic', add drama, atmosphere, and a painterly feel. If 'realistic', make it look like a real, high-end 8K photoshoot.\n\n"
            f"--- Color & Tone ---\n"
            f"Apply this specific color grade and mood: **{color_tone}**. If '{color_tone}' is 'No preference' or blank, use a color tone that best matches the **{theme}**.\n\n"
            f"--- Image Usage ---\n"
            f"The image will be used for: **{usage}**. Adapt the composition accordingly: "
            f"  - 'Profile Picture': A powerful, closer-up medium shot or headshot. "
            f"  - 'Social Media Post': A dynamic 1:1 square composition. "
            f"  - 'Social Media Story': A 9:16 vertical composition. "
            f"  - 'Print': Maximum 8K detail, ultra-high resolution. "
            f"  - 'Just for fun': A standard, well-balanced shot.\n\n"
        )

        # [NEW] Append custom prompt if it exists
        if custom_prompt:
            prompt += (
                f"--- Additional User Instructions ---\n"
                f"{custom_prompt}\n\n"
            )

        # Final instruction
        prompt += (
            f"--- Final Instruction ---\n"
            f"Combine all elements. Change the clothing and background to be 100% appropriate for the **{theme}** and **{look}**. "
            f"**Repeat: Keep the subject's original face and identity perfectly recognizable.**"
        )
        
        # --- End of [MODIFIED] prompt ---


        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                ]
            }],
            "generationConfig": {
                "temperature": 0.6,
                "topP": 0.9,
                "topK": 40
            },
        }
        headers = {"Content-Type": "application/json"}

        # Added connection resilience
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=(10, 180)  # (connect_timeout, read_timeout)
            )
        except requests.exceptions.Timeout:
            print("[ERROR] Gemini API request timed out.")
            return jsonify({"error": "Image generation timed out. Please try again."}), 504
        except requests.exceptions.ConnectionError as ce:
            print(f"[ERROR] Connection reset or dropped: {ce}")
            return jsonify({"error": "Connection to image generator lost. Try again."}), 502
        except Exception as e:
            print(f"[ERROR] Unexpected network error: {e}")
            return jsonify({"error": f"Network error: {str(e)}"}), 500

        # Handle Gemini response
        if response.status_code != 200:
            print(f"[ERROR] Gemini API Error {response.status_code}: {response.text}")
            return jsonify({"error": f"Gemini API returned {response.status_code}", "details": response.text}), response.status_code

        result = response.json()

        # Safety check
        if "promptFeedback" in result:
            print(f"[WARN] Gemini promptFeedback: {result['promptFeedback']}")
            block_reason = result.get("promptFeedback", {}).get("blockReason", "Unknown")
            if block_reason == "SAFETY" and not result.get("candidates"):
                return jsonify({"error": f"Blocked by safety filter: {block_reason}"}), 400

        candidates = result.get("candidates", [])
        if not candidates:
            feedback = result.get("promptFeedback", "No feedback")
            print("[WARN] Gemini returned no candidates.")
            return jsonify({"error": "No output from Gemini", "details": feedback}), 400

        parts = candidates[0].get("content", {}).get("parts", [])
        gen_b64 = None
        for part in parts:
            if "inline_data" in part:
                gen_b64 = part["inline_data"]["data"]
                break
            elif "inlineData" in part: # Handle both casings
                gen_b64 = part["inlineData"]["data"]
                break

        if not gen_b64:
            return jsonify({"error": "Gemini returned no image data"}), 400

        # Save generated image
        generated_filename = f"gen_{int(time.time())}_{secure_filename(theme.split(' ')[0])}.jpg"
        generated_path = os.path.join(app.config['GENERATED_FOLDER'], generated_filename)
        with open(generated_path, "wb") as f:
            f.write(base64.b64decode(gen_b64))

        generated_url = f"/generated/{generated_filename}"

        # Update credits + history safely
        # We fetch the user again *inside* the session to be safe
        user_to_update = db.session.get(User, current_user.id)
        if not user_to_update:
             return jsonify({"error": "User not found during credit update"}), 500
             
        user_to_update.credits -= IMAGE_COST
        
        # [MODIFIED] Use the 'theme' as the title for history
        history_title = f"{theme.title()} ({look.title()})"
        new_history_item = SearchHistory(
            title=history_title,
            prompt_content=prompt, # Save the full prompt
            generated_result=generated_url,
            user_id=user_to_update.id
        )
        db.session.add(new_history_item)
        db.session.commit()
        
        new_credit_count = user_to_update.credits
        db.session.close() # Close session after commit

        print(f"[INFO] Generation complete for {user_to_update.username}: {generated_filename} (Credits left: {new_credit_count})")

        return jsonify({
            "message": "Image generated successfully",
            "generated_image_url": generated_url,
            "new_credit_count": new_credit_count,
            "prompt_for_history": prompt, # [NEW] Send prompt back to frontend
            "title_for_history": history_title # [NEW] Send title back to frontend
        }), 200

    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
        db.session.rollback() # Rollback any partial db changes on error
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


# ------------------------
# ✅ Server Runner
# ------------------------
if __name__ == "__main__":
    # The db.create_all() here is fine for local dev.
    # The one inside the app_context at the top handles the Gunicorn boot.
    with app.app_context():
        print("Checking/creating database tables for local run...")
        db.create_all()
        print("Database ready.")
    
    # Use 0.0.0.0 to be accessible externally (like Gunicorn does)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)












