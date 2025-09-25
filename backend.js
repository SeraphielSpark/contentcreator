import express from "express";
import bodyParser from "body-parser";
import cors from "cors";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(bodyParser.json());

// Gemini setup
const genAI = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY });

app.post("/generate", async (req, res) => {
  try {
    const { content } = req.body;
    if (!content) return res.status(400).json({ error: "Content is required" });

    const prompt = `
      Extract 10 SEO-friendly hashtags from the following content.
      Return hashtags only, separated by commas. Content: "${content}"
    `;

    // Generate content using GenAI Node.js SDK
    const response = await genAI.models.generateContent({
      model: "gemini-1.5-flash",
      contents: [{ type: "text", text: prompt }],
    });

    // The generated text is inside response.candidates[0].content
    const generatedText = response.candidates?.[0]?.content?.[0]?.text;
    if (!generatedText) return res.status(500).json({ error: "No text generated" });

    const hashtags = generatedText
      .replace(/\n/g, '')
      .split(/,|\s(?=#)/)
      .map(tag => tag.trim())
      .filter(tag => tag.startsWith("#"));

    res.json({ hashtags });
  } catch (error) {
    console.error("❌ Gemini API Error:", error);
    res.status(500).json({ error: "Something went wrong" });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Backend running at http://localhost:${PORT}`);
});
