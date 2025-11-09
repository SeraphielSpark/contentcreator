import os
import io
import time
import uuid
import base64
import requests
import json
import random 
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, render_template_string
from flask_cors import CORS, cross_origin 
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
from jwt import ExpiredSignatureError, decode
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail, Message

# CRITICAL FIX: Import the Client directly from the correct location
from google.genai import Client as GenAIClient

# ------------------------
# Helper for optional JWT
# ------------------------
def get_jwt_identity_optional():
    """Retrieves JWT identity if token is present, otherwise returns None."""
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except (NoAuthorizationError, ExpiredSignatureError):
        return None

# ------------------------
# Flask App Setup
# ------------------------
app = Flask(__name__)

# --- App Configuration ---
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback_secret_key_123")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "super-secret-key") 
app.config["FRONTEND_URL"] = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5500") 

# --- Email Configuration ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))

# --- Folder Configuration ---
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
app.config['UPLOAD_FOLDER'] = os.path.abspath(UPLOAD_FOLDER)
app.config['GENERATED_FOLDER'] = os.path.abspath(GENERATED_FOLDER)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

# --- Database Path ---
db_path = os.path.join("/tmp", "app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{db_path}") 

# ------------------------
# Google API Configuration
# ------------------------
MODEL_NAME = "gemini-2.5-flash-image" 
GOOGLE_API_KEY1 = os.environ.get("GEMINI")
if not GOOGLE_API_KEY1:
    print("[FATAL ERROR] GEMINI (for Image API) is not set.")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY1}"

# ------------------------
# Database & Add-on Setup
# ------------------------
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
mail = Mail(app)
oauth = OAuth(app)
# In-memory storage for chat history/context
chat_histories = {} 

# UNIVERSAL CORS FIX: Apply the widest CORS possible using the core config.
CORS(app, 
    supports_credentials=True, 
    resources={r"/*": {"origins": [
        "https://www.creatorsai.ai",
        "https://creatorsai.ai",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        os.environ.get("FRONTEND_URL", "*") 
    ]}}
)
# Note: The @cross_origin decorators are now technically redundant but kept for maximum safety.

# Configure Google OAuth
oauth.register(
    name='google',
    client_id= os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ------------------------
# Database Models 
# ------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True) 
    searches = db.relationship('SearchHistory', backref='author', lazy=True)
    plan = db.Column(db.String(100), nullable=False, default='free')
    credits = db.Column(db.Integer, nullable=False, default=200)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    oauth_provider = db.Column(db.String(50), nullable=True)
    oauth_provider_id = db.Column(db.String(200), nullable=True)
    verification_otp = db.Column(db.String(255), nullable=True) 
    otp_expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"User('{self.email}', Provider: {self.oauth_provider}, Verified: {self.is_verified})"

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    prompt_content = db.Column(db.Text, nullable=False)
    generated_result = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'prompt_content': self.prompt_content,
            'generated_result': self.generated_result,
            'timestamp': self.timestamp.isoformat()
        }
# ------------------------
# Create Tables & JWT Config 
# ------------------------
with app.app_context():
    print("[INFO] Initializing database tables...")
    db.create_all()
    print("[INFO] Database tables initialized.")

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    try:
        return User.query.get(int(identity))
    except (ValueError, TypeError):
        return None

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "✅ CreatorsAI API is live!"})

# ---------------------------------
# AUTH FLOW: STEP 1 (Send OTP)
# ---------------------------------
@app.route("/auth/register/send-otp", methods=["POST"]) 
@cross_origin() 
def register_send_otp():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    
    if user and user.is_verified and user.password:
        return jsonify({"msg": "An account with this email already exists."}), 400
    
    if user and user.oauth_provider and user.is_verified:
        return jsonify({"msg": "An account with this email already exists via social login. Please use the Google sign-in button."}), 400

    otp = str(random.randint(100000, 999999))
    hashed_otp = bcrypt.generate_password_hash(otp).decode("utf-8")
    otp_expiration = datetime.utcnow() + timedelta(minutes=10)
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    if user:
        user.password = hashed_password
        user.verification_otp = hashed_otp
        user.otp_expires_at = otp_expiration
        db.session.add(user)
    else:
        new_user = User(email=email, password=hashed_password, plan="free", credits=200, is_verified=False, verification_otp=hashed_otp, otp_expires_at=otp_expiration)
        db.session.add(new_user)

    # Send verification email with OTP
    try:
        msg = Message('Your CreatorsAI Verification Code', recipients=[email])
        msg.body = f"Welcome to CreatorsAI!\n\nYour verification code is: {otp}\n\nThis code will expire in 10 minutes."
        mail.send(msg) 
        db.session.commit()
        db.session.close()
        return jsonify({"msg": "OTP sent! Check your email. It will expire in 10 minutes."}), 200
        
    except Exception as e:
        db.session.rollback()
        db.session.close()
        print(f"[FATAL ERROR] Failed to send email via SMTP: {e}")
        # Return 500 status code on critical email failure
        return jsonify({"msg": "Could not send verification email. Please check server logs for SMTP error."}), 500

# ------------------------------------
# AUTH FLOW: STEP 2 (Verify OTP)
# ------------------------------------
@app.route("/auth/register/verify-otp", methods=["POST"])
@cross_origin()
def register_verify_otp():
    data = request.get_json() or {}
    email = data.get("email"); otp = data.get("otp")
    if not email or not otp: return jsonify({"msg": "Email and OTP are required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"msg": "User not found. Please sign up again."}), 404
    if user.is_verified: return jsonify({"msg": "User is already verified. Please log in."}), 400
    if not user.verification_otp or not user.otp_expires_at: return jsonify({"msg": "No pending verification. Please sign up again."}), 400
    if datetime.utcnow() > user.otp_expires_at: return jsonify({"msg": "Your OTP has expired. Please sign up again to get a new one."}), 401
    if not bcrypt.check_password_hash(user.verification_otp, otp): return jsonify({"msg": "Invalid OTP."}), 401
    user.is_verified = True; user.verification_otp = None; user.otp_expires_at = None; db.session.commit()
    access_token = create_access_token(identity=str(user.id))
    user_info = { "id": user.id, "email": user.email, "plan": user.plan, "credits": user.credits, 'access_token': access_token }
    db.session.close()
    return jsonify(user_info), 200

# ----------------------------
# Email Login endpoint
# ----------------------------
@app.route("/auth/login", methods=["POST"])
@cross_origin()
def login():
    data = request.get_json()
    email = data.get("email"); password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"msg": "Invalid credentials"}), 401
    if not user.password: return jsonify({"msg": "This account was created via social login. Please use the Google sign-in button."}), 401
    if not bcrypt.check_password_hash(user.password, password): return jsonify({"msg": "Invalid credentials"}), 401
    if not user.is_verified: return jsonify({"msg": "Please verify your email address before logging in."}), 401
    token = create_access_token(identity=str(user.id))
    user_info = { "id": user.id, "email": user.email, "plan": user.plan, "credits": user.credits, 'access_token': token }
    db.session.close()
    return jsonify(user_info), 200

# ----------------------------
# Social Login Routes
# ----------------------------
@app.route('/auth/google/login')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        if not token or 'id_token' not in token: raise Exception("Google token response is invalid or missing ID token.")
        user_info = oauth.google.parse_id_token(token, nonce=None)
        user_email = user_info['email']; user_google_id = user_info['sub']
        user = User.query.filter_by(email=user_email).first()
        if not user: user = User(email=user_email, oauth_provider='google', oauth_provider_id=user_google_id, is_verified=True, plan='free', credits=200); db.session.add(user)
        elif user and not user.oauth_provider: user.oauth_provider = 'google'; user.oauth_provider_id = user_google_id; user.is_verified = True
        elif user and user.oauth_provider == 'google' and user.oauth_provider_id != user_google_id: user.oauth_provider_id = user_google_id
        user.is_verified = True; db.session.commit()
        access_token = create_access_token(identity=str(user.id))
        user_data = { "id": user.id, "email": user.email, "plan": user.plan, "credits": user.credits, 'access_token': access_token }
        # The correct FRONTEND_URL is used here for postMessage security
        popup_response_script = f"""<html><head><title>Authenticating...</title><script>const targetOrigin = '{app.config["FRONTEND_URL"]}'; window.opener.postMessage({{ type: 'auth_success', payload: {json.dumps(user_data)} }}, targetOrigin); window.close();</script></head><body>Success! Logging you in...</body></html>"""
        return render_template_string(popup_response_script)
    except Exception as e:
        print(f"[ERROR] Google OAuth failed: {e}"); db.session.rollback()
        popup_error_script = f"""<html><head><title>Error</title><script>const targetOrigin = '{app.config["FRONTEND_URL"]}'; window.opener.postMessage({{ type: 'auth_error', payload: {{ "msg": "Social login failed. Please try again." }} }}, targetOrigin); window.close();</script></head><body>Error. Please try again.</body></html>"""
        return render_template_string(popup_error_script), 500
    finally:
        db.session.close()

# ------------------------
# All other routes
# ------------------------

# Conversation History and Context Management
@app.route("/generate", methods=["POST"])
@cross_origin()
def generate():
    data = request.get_json(silent=True) or {}
    content = (data.get("post") or "").strip()
    if not content: return jsonify(error="Content required (must be sent as 'post')"), 400
    
    chat_prompt = ("You are an expert social media strategist.\n" + f"Your task is to extract exactly 7 SEO-optimized hashtags for: \"{content}\".\n" + "RULES:\n1. Return ONLY the hashtags.\n2. Each hashtag must start with a #.\n3. Separate each hashtag with a comma.\n4. Do not include any other text, titles, or explanations.\n")

    try:
        GOOGLE_API_KEY = os.environ.get("GEMINI")
        if not GOOGLE_API_KEY:
            print("[FATAL ERROR] GOOGLE_API_KEY is not set. Please add it in Render Environment Variables.")
            return jsonify({"error": "API Key not configured"}), 500
        
        client = GenAIClient(api_key=GOOGLE_API_KEY) 
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=chat_prompt)
        model_output = response.text.strip() if response.text else ""
        hashtags = [h.strip() for h in model_output.split(",") if h.strip().startswith("#")]
        if not hashtags:
            print(f"Model returned unexpected output: {model_output}")
            return jsonify(error="Failed to parse hashtags from model response", model_output=model_output), 500
        return jsonify(hashtags=hashtags)
    except Exception as e:
        print(f"[ERROR] /generate: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/respond", methods=["POST"])
@cross_origin()
def respond():
    data = request.get_json() or {}
    prompt_content = data.get("prompt", "").strip()
    max_sentences = int(data.get("max_sentences", 2))
    chat_id = data.get("chat_id")
    if not prompt_content: return jsonify({"error": "No prompt content provided"}), 400
    
    # 1. Manages and creates chat context using the in-memory chat_histories dictionary
    if not chat_id: chat_id = str(uuid.uuid4()); chat_histories[chat_id] = []
    chat_histories.setdefault(chat_id, [])
    
    # Append user's message
    chat_histories[chat_id].append({"role": "user", "text": prompt_content})
    
    # Create conversation history string for the model (maintaining context)
    history_text = "\n".join([f"{'USER' if msg['role'] == 'user' else 'AI'}: {msg['text']}" for msg in chat_histories[chat_id]])
    
    # 2. Construct the prompt with the full history
    chat_prompt = f"""
You are CreatorsAI — precise, concise, and friendly.

TASK:
- Respond naturally in Markdown (use headings, bold, lists, paragraphs)
- Keep each response within {max_sentences} sentences
- Based on the CONVERSATION HISTORY, understand the continuity and context of the user's question.

CONVERSATION HISTORY:
{history_text}

USER QUESTION:
"{prompt_content}"
"""
    
    try:
        GEMINI_API_KEY = os.environ.get("GEMINI")
        if not GEMINI_API_KEY: raise RuntimeError("GEMINI API key is not set in environment variables.")
        
        client = GenAIClient(api_key=GEMINI_API_KEY) 
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[chat_prompt])
        result_text = response.text.strip() if response.text else ""
        
        # Append AI's response to maintain continuity
        chat_histories[chat_id].append({"role": "ai", "text": result_text})
        
        return jsonify({"result": result_text, "meta": {"chat_id": chat_id, "max_sentences": max_sentences}}), 200 
    except Exception as e:
        print(f"[ERROR] /respond: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/history", methods=["POST"])
@jwt_required()
@cross_origin()
def save_history():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user: return jsonify({"error": "User not found"}), 404
    data = request.get_json()
    prompt = data.get("prompt"); result = data.get("result"); title = data.get("title")
    if not prompt or not result or not title: return jsonify({"error": "Title, prompt, and result required"}), 400
    new_item = SearchHistory(title=title, prompt_content=prompt, generated_result=result, author=user)
    db.session.add(new_item); db.session.commit(); db.session.close()
    return jsonify({"message": "History saved", "history_id": new_item.id}), 201

@app.route("/api/history", methods=["GET"])
@jwt_required()
@cross_origin() 
def get_history():
    user_id = get_jwt_identity()
    items = SearchHistory.query.filter_by(user_id=user_id).order_by(SearchHistory.timestamp.desc()).all()
    db.session.close()
    return jsonify([item.to_dict() for item in items]), 200

@app.route('/upload-reference', methods=['POST'])
@jwt_required(optional=True)
@cross_origin()
def upload_reference():
    try:
        if 'file' not in request.files: return jsonify({"error": "No file uploaded"}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({"error": "Empty filename"}), 400
        filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return jsonify({"message": "File uploaded successfully", "filename": filename, "url": f"/uploads/{filename}"}), 200
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/generate-image', methods=['POST'])
@jwt_required()
@cross_origin()
def generate_image():
    IMAGE_COST = 10
    current_user = db.session.get(User, int(get_jwt_identity()))
    if not current_user: return jsonify({"error": "User not found"}), 404
    if current_user.credits < IMAGE_COST: return jsonify({"error": "Not enough credits"}), 403
    try:
        data = request.json
        ref_filename = data.get("reference_filename"); category = data.get("category"); theme = data.get("theme"); look = data.get("look"); color_tone = data.get("color_tone"); usage = data.get("usage"); custom_prompt = data.get("custom_prompt")
        if not all([ref_filename, category, theme, look, usage]): return jsonify({"error": "Missing required fields"}), 400
        artist = "a world-class digital artist and photo-manipulation expert"
        ref_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(ref_filename))
        if not os.path.exists(ref_path): return jsonify({"error": "Reference image not found"}), 404
        with Image.open(ref_path) as img:
            buffer = io.BytesIO()
            img.thumbnail((1024, 1024))
            img.convert("RGB").save(buffer, format="JPEG", quality=90)
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        prompt = (
            f"You are {artist}.\n"
            f"Your task is to transform the person in the reference photo according to the user's request. "
            f"**The most important rule is to strictly maintain their exact face, features, expression, and identity. DO NOT change their face.**\n\n"
            f"--- Main Category ---\n"
            f"The desired category is: **{category}**.\n\n"
            f"--- Main Theme ---\n"
            f"The desired theme is: **{theme}**.\n\n"
            f"--- Desired Look ---\n"
            f"The final image must have a **{look}** look.\n\n"
            f"--- Color & Tone ---\n"
            f"Apply this specific color grade and mood: **{color_tone}**.\n\n"
            f"--- Image Usage ---\n"
            f"The image will be used for: **{usage}**.\n\n"
            + (f"--- Additional User Instructions ---\n{custom_prompt}\n\n" if custom_prompt else "") +
            f"--- Final Instruction ---\n"
            f"Combine all elements. Change the clothing and background to be 100% appropriate for the **{theme}** and **{look}**. "
            f"**Repeat: Keep the subject's original face and identity perfectly recognizable.**"
        )

        payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}]}]}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=(10, 180))
        if response.status_code != 200: return jsonify({"error": f"Gemini API returned {response.status_code}", "details": response.text}), response.status_code
        result = response.json()
        
        gen_b64 = next((part.get("inline_data", {}).get("data") for part in result.get("candidates", [])[0].get("content", {}).get("parts", []) if "inline_data" in part), None)
        if not gen_b64: return jsonify({"error": "Gemini returned no image data"}), 400
        generated_filename = f"gen_{int(time.time())}_{secure_filename(theme.split(' ')[0])}.jpg"
        generated_path = os.path.join(app.config['GENERATED_FOLDER'], generated_filename)
        with open(generated_path, "wb") as f: f.write(base64.b64decode(gen_b64))
        generated_url = f"/generated/{generated_filename}"
        current_user.credits -= IMAGE_COST
        new_history_item = SearchHistory(title=f"{theme.title()} ({look.title()})", prompt_content=prompt, generated_result=generated_url, author=current_user)
        db.session.add(new_history_item); db.session.commit(); db.session.close()
        return jsonify({"message": "Image generated successfully", "generated_image_url": generated_url, "new_credit_count": current_user.credits}), 200
    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
        db.session.rollback(); db.session.close()
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/generated/<path:filename>')
def serve_generated(filename):
    return send_from_directory(app.config['GENERATED_FOLDER'], filename)

# ------------------------
# Server Runner
# ------------------------
if __name__ == "__main__":
    with app.app_context():
        print("Checking/creating database tables for local run...")
        db.create_all()
        print("Database ready.")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
