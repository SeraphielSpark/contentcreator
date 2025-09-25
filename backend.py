import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai  # latest SDK

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
PORT = int(os.getenv("PORT", 5000))

if not API_KEY:
    raise Exception("GOOGLE_API_KEY not set in environment variables!")

# Initialize Google GenAI client
client = genai.Client(api_key=API_KEY)

# FastAPI app
app = FastAPI(title="Content Creator Assistance API")

# CORS setup (allow all origins, customize if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model
class ContentRequest(BaseModel):
    content: str

# POST endpoint to generate SEO hashtags
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
        # Correct usage with latest SDK
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[{"type": "text", "text": prompt}]
        )

        # Extract generated text
        generated_text = response.output[0].content[0].text.strip() if response.output else ""
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

# Run locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
