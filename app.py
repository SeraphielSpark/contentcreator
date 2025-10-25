from flask import Flask, request, jsonify
import google.genai as genai  # <-- Real import
import os
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
# --- CHANGED LINE ---
# We need to import these to catch expired/invalid tokens
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import ExpiredSignatureError
from datetime import datetime, timedelta

# --- Helper Function (UPDATED) ---
def get_jwt_identity_optional():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    # --- CHANGED LINE ---
    # Now catches missing, invalid, or expired tokens and treats them all as "guest"
    except (NoAuthorizationError, ExpiredSignatureError):
        return None

app = Flask(__name__)

# --- CORS Configuration ---
CORS(app)
# Example for specific origin:
# CORS(app, origins=["http://127.0.0.1:5500", "http://localhost:5500"], supports_credentials=True)

# --- App Configuration ---
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a_very_strong_fallback_secret_key_123")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///site.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "a_super_secret_jwt_key_456")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)

# --- *** REAL GenAI Configuration *** ---
# IMPORTANT: Set the GOOGLE_API_KEY environment variable in your terminal
# export GOOGLE_API_KEY='your_actual_api_key_here'
try:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("[FATAL ERROR] GOOGLE_API_KEY environment variable not set. API calls will fail.")
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"[ERROR] Failed to configure Google GenAI: {e}")
# --- End GenAI Configuration ---

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# --- Database Models ---
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

# --- JWT User Loaders ---
@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)

# --- Home Route ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "CreatorsAI API is live!"})


# --- (MockGenAIClient class removed) ---


# --- Original Generate Route (for SEO tags, etc.) ---
@app.route("/generate", methods=["POST"])
def generate():
    print("\n--- Request received at /generate ---")
    data = request.get_json()
    if not data:
        print("[ERROR] /generate: No JSON data received")
        return jsonify({"error": "Request must be JSON"}), 400

    post_content = data.get("post", "")
    print(f"[DEBUG] /generate: Received post content: {post_content[:2000]}...")

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
        # --- *** REAL GenAI Call *** ---
        print("[DEBUG] /generate: Calling Google GenAI...")

        # Select the model (e.g., 'gemini-1.5-flash-latest' for speed)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # Send the prompt to the API
        response = model.generate_content(prompt)

        result = response.text.strip()
        # --- *** End REAL GenAI Call *** ---

        print(f"[DEBUG] /generate: Responding with result: {result[:2000]}...")
        return jsonify({"result": result})

    except Exception as e:
        print(f"[ERROR] /generate: Exception occurred: {str(e)}")
        # Check for common API key errors
        if "API_KEY" in str(e) or "PERMISSION_DENIED" in str(e):
            print("[ERROR] /generate: Google API Key error.")
            return jsonify({"error": "Invalid or missing Google API Key. Check server logs."}), 500
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500


# --- *** NEW CHAT RESPONSE ROUTE *** ---
@app.route("/respond", methods=["POST"])
def respond():
    print("\n--- Request received at /respond ---")
    data = request.get_json()
    if not data:
        print("[ERROR] /respond: No JSON data received")
        return jsonify({"error": "Request must be JSON"}), 400

    prompt_content = data.get("prompt", "")
    print(f"[DEBUG] /respond: Received prompt: {prompt_content[:2000]}...")

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
        # --- ✅ Correct Google GenAI SDK Call ---
        print("[DEBUG] /respond: Calling Google GenAI...")
        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=chat_prompt
        )

        result = response.text.strip() if hasattr(response, "text") else "No response text received."
        print(f"[DEBUG] /respond: GenAI response received: {result[:2000]}...")

        return jsonify({"result": result})

    except Exception as e:
        print(f"[ERROR] /respond: Exception occurred: {str(e)}")
        if "API_KEY" in str(e) or "PERMISSION_DENIED" in str(e):
            print("[ERROR] /respond: Google API Key error.")
            return jsonify({"error": "Invalid or missing Google API Key. Check server logs."}), 500
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

# --- Auth Routes ---
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

# --- Protected History Routes ---
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


# --- Main App Runner ---
if __name__ == "__main__":
    with app.app_context():
        print("Creating database tables if they don't exist...")
        try:
            db.create_all()
            print("Database tables checked/created.")
        except Exception as e:
            print(f"Error creating database tables: {e}")

    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask app on host 0.0.0.0, port {port} with debug mode...")
    # Use debug=True for development to see errors and auto-reload
    app.run(host="0.0.0.0", port=port, debug=True)


