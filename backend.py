import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google.genai import Client

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
PORT = int(os.getenv("PORT", 5000))

if not API_KEY:
    raise Exception("GOOGLE_API_KEY not set in environment variables!")

# Initialize Google GenAI client
client = Client(api_key=API_KEY)

# FastAPI app
app = FastAPI(title="Content Creator Assistance API")

# CORS (allow all origins; customize if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model
class ContentRequest(BaseModel):
    content: str

# Endpoint
@app.post("/generate")
async def generate_hashtags(request: ContentRequest):
    content = request.content
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    prompt = f"""
    Extract 10 SEO-friendly hashtags from the following content.
    Return hashtags only, separated by commas. Content: "{content}"
    """

    try:
        response = client.generate_text(
            model="gemini-1.5",
            content=prompt
        )

        # Extract text
        generated_text = response.text.strip() if response.text else ""
        if not generated_text:
            return {"hashtags": []}

        # Clean and split hashtags
        hashtags = [
            tag.strip() for tag in generated_text.replace("\n", "").split(",")
            if tag.strip().startswith("#")
        ]

        return {"hashtags": hashtags}

    except Exception as e:
        print("❌ Gemini API Error:", e)
        raise HTTPException(status_code=500, detail="Something went wrong")

# Run locally (optional)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
