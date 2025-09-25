import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
PORT = int(os.getenv("PORT", 5000))

if not API_KEY:
    raise Exception("GOOGLE_API_KEY not set!")

# Initialize client
client = genai.Client(api_key=API_KEY)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContentRequest(BaseModel):
    content: str

@app.post("/generate")
async def generate_hashtags(request: ContentRequest):
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    prompt = f"Extract 10 SEO-friendly hashtags from the following content. Return hashtags only, separated by commas. Content: {content}"

    try:
        # Using the new SDK method: pass a list of TextPrompt objects
        response = client.responses.create(
            model="gemini-1.5",
            input=[genai.TextPrompt(prompt)]
        )

        # Extract the output text
        generated_text = response.output_text  # this is the correct property now

        # Split into hashtags
        hashtags = [tag.strip() for tag in generated_text.replace("\n", "").split(",") if tag.strip().startswith("#")]

        return {"hashtags": hashtags}

    except Exception as e:
        print("❌ Gemini API Error:", e)
        raise HTTPException(status_code=500, detail="Something went wrong")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
