import os
from fastapi import FastAPI, HTTPException
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

app = FastAPI(title="Content Creator Assistance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContentRequest(BaseModel):
    content: str

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
        # Correct method for latest SDK
        response = client.text.generate(
            model="gemini-1.5",
            temperature=0,
            max_output_tokens=200,
            prompt=prompt
        )

        generated_text = response.output[0].content[0].text.strip() if response.output else ""
        if not generated_text:
            return {"hashtags": []}

        hashtags = [
            tag.strip() for tag in generated_text.replace("\n", "").split(",")
            if tag.strip().startswith("#")
        ]

        return {"hashtags": hashtags}

    except Exception as e:
        print("❌ Gemini API Error:", e)
        raise HTTPException(status_code=500, detail="Something went wrong")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
