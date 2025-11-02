
import fs from "fs";
import path from "path";
import axios from "axios";
import dotenv from "dotenv";
dotenv.config();

const FEED_PATH = path.join(process.cwd(), "feed.csv");

export async function getProductData() {
  const csv = fs.readFileSync(FEED_PATH, "utf-8");
  const lines = csv.split("\n").slice(1);
  const products = lines.map((line) => {
    const [title, , , image, price, url, description, , , , , category] = line.split(",");
    return { title, image, price, url, description, category };
  });
  return products;
}

export async function chatWithGemini(userMessage) {
  const prompt = `
  You are an AI eCommerce assistant named ${process.env.CHATBOT_NAME}.
  Use the following CJ Dropshipping product data to answer questions, recommend products, and upsell related items.

  User message: "${userMessage}"

  If the user asks about a product, match titles, categories, or descriptions from the feed.
  If asking for recommendations, show 2-3 top-rated or trending products with links and short suggestions.
  Always use a friendly, confident tone.
  Reply in Markdown.
  `;

  try {
    const res = await axios.post(
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
      { contents: [{ parts: [{ text: prompt }] }] },
      { headers: { "Content-Type": "application/json", "x-goog-api-key": process.env.GEMINI_API_KEY } }
    );

    const aiReply = res.data?.candidates?.[0]?.content?.parts?.[0]?.text || "I'm here to help!";
    return aiReply;
  } catch (err) {
    console.error("⚠️ Gemini Chat Error:", err.message);
    return "Sorry, I couldn’t connect to the AI service. Please try again.";
  }
}
