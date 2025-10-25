from flask import Flask, request, jsonify
from google import genai  # ✅ Correct import for Google GenAI SDK
import os
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

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fallback_secret_key_123")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///site.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "fallback_jwt_secret_456")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)

# ------------------------
# ✅ Google GenAI Configuration
# ------------------------
try:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("[FATAL ERROR] GOOGLE_API_KEY is not set. Please add it in Render Environment Variables.")
    client = genai.Client(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"[ERROR] Failed to initialize Google GenAI client: {e}")
    client = None

# ------------------------
# ✅ Database Setup
# ------------------------
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)


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
    return jsonify({"message": "CreatorsAI API is live on Render!"})


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
        response = client.models.generate_content(
            model="gemini-2.0-flash",
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
        response = client.models.generate_content(
            model="gemini-2.0-flash",
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


# ------------------------
# ✅ Server Runner for Render
# ------------------------
if __name__ == "__main__":
    with app.app_context():
        print("Checking/creating database tables...")
        db.create_all()
        print("Database ready.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
