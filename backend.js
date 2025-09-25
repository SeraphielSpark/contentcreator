import express from "express";
import bodyParser from "body-parser";
import cors from "cors";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// Gemini setup
const genAI = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY });

// Endpoint
app.post("/generate", async (req, res) => {
  try {
    const { content } = req.body;
    if (!content) return res.status(400).json({ error: "Content is required" });

    const prompt = `
      Extract 10 SEO-friendly hashtags from the following content.
      Return hashtags only, separated by commas. Content: "${content}"
    `;

    // Generate content using the new GenAI method
    const response = await genAI.generateText({
      model: "gemini-1.5", // or "gemini-1.5-flash" if available
      input: prompt
    });

    // Optional: Clean response
    const hashtags = response.output_text
      .replace(/\n/g, '')
      .split(/,|\s(?=#)/)  // split by commas or spaces before # signs
      .map(tag => tag.trim())
      .filter(tag => tag.startsWith("#"));

    res.json({ hashtags });
  } catch (error) {
    console.error("❌ Gemini API Error:", error);
    res.status(500).json({ error: "Something went wrong" });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Backend running at http://localhost:${PORT}`);
});
