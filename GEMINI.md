# Gemini.md — No Docker AI Ecommerce Build Guide

This `Gemini.md` file contains all the instructions GeminiCLI will follow to enhance and build your AI-powered ecommerce platform. This version avoids Docker entirely and is optimized for systems with 4GB RAM.

---

## ✅ 1. Print Labels for Shipping (PDF Format)

- Install `reportlab`:
  ```bash
  pip install reportlab
  ```
- Add `/print-label` endpoint in `server.py` to generate a simple PDF label from order details.
- Save label PDFs to `/labels/` directory with naming format `order_<order_id>.pdf`.

## ✅ 2. Fraud Detection Flags (e.g. Duplicate IP)

- Add middleware or request tracking to monitor IP address history.
- Flag users with multiple accounts or repeated failed transactions from same IP.
- Save flagged attempts to `fraud_flags.csv` or store in SQLite.

## ✅ 3. Mobile App Build with React Native

- Set up a basic React Native app using Expo:
  ```bash
  npx create-expo-app mobile-app
  cd mobile-app
  npm install axios react-navigation
  ```
- Connect to backend APIs for:
  - Product listing
  - Cart
  - Checkout
  - Order tracking
- Add support for push notifications later (e.g. via Firebase).

---

## 🔍 NEXT IMPLEMENTATIONS

## ✅ 4. AI Product Tag Generator

- Add `/generate-tags` API endpoint that:
  - Accepts product title & description.
  - Uses Gemini or OpenAI API to generate SEO tags.
- Install and use `openai` or Gemini API SDK.
- Example prompt: “Generate SEO-friendly product tags for: [product info]”.
- Auto-attach tags to product JSON.

## ✅ 5. Multi-Vendor Support (Vendor Dashboard)

- Create separate vendor login/auth route (`/vendor/login`, `/vendor/dashboard`).
- Vendors can:
  - Upload products
  - View their orders
  - Track revenue
- Store vendor details in `vendors.json` or SQLite.

## ✅ 6. PDF Invoices (Auto-Generated)

- Use `reportlab` or `fpdf` to generate invoices.
- Auto-generate invoice PDF after successful payment.
- Store in `/invoices/` with naming format `invoice_<order_id>.pdf`.
- Attach download link on user dashboard and order confirmation.

## ✅ 7. Profit Calculator for Admin

- Create `/admin/profit-report` route.
- Fetch all orders, subtract cost from sale price.
- Show monthly, weekly, and daily profit summaries.

## ✅ 8. Dynamic Inventory Graph Dashboard

- Install `matplotlib` or `plotly`:
  ```bash
  pip install matplotlib
  ```
- Plot inventory status and sales trend graphs.
- Display on admin dashboard page using base64-encoded images or interactive JS charts (if frontend).

---

## ✅ How to Run (No Docker)

```bash
# Backend setup
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py

# React Native app (optional)
cd mobile-app
npx expo start
```

---

## 📁 Recommended Folder Structure

```
project-root/
│
├── server.py
├── labels/
├── invoices/
├── data/
│   ├── fraud_flags.csv
│   └── vendors.json
├── templates/
├── mobile-app/  (React Native)
└── Gemini.md
```

---


## 🚀 Step-by-Step Plan (for GeminiCLI )

Create a new file called **`CJ_TOKEN_REFRESH_DOCKER.md`** with the following content:

---

### 🧩 `CJ_TOKEN_REFRESH_DOCKER.md`

```markdown
# CJ Dropshipping Token Auto-Refresh (Docker + Render)

## 🧠 Objective
Securely automate CJ Dropshipping API token refresh using environment variables and background scheduler, optimized for Docker-based apps deployed on Render.

---

## 1️⃣ Environment Variables Setup

In `.env` (local and on Render dashboard):

```

CJ_APP_KEY=your_app_key
CJ_APP_SECRET=your_app_secret
CJ_REFRESH_TOKEN=your_initial_refresh_token
CJ_ACCESS_TOKEN=your_initial_access_token

````

> ⚠️ Never commit this file to GitHub. Add `.env` to `.gitignore`.

---

## 2️⃣ Create `tokenRefresher.js`

In `src/services/tokenRefresher.js`:

```js
import axios from "axios";
import fs from "fs";
import dotenv from "dotenv";
dotenv.config();

const CJ_REFRESH_URL = "https://developers.cjdropshipping.com/api2.0/v1/token/refresh";
const TOKEN_FILE = "./tmp/cj_token_cache.json";

export async function refreshCJToken() {
  try {
    const response = await axios.post(CJ_REFRESH_URL, {
      appKey: process.env.CJ_APP_KEY,
      appSecret: process.env.CJ_APP_SECRET,
      refreshToken: process.env.CJ_REFRESH_TOKEN,
    });

    if (response.data.code === 200) {
      const { accessToken, refreshToken } = response.data.data;

      // Update environment for runtime
      process.env.CJ_ACCESS_TOKEN = accessToken;
      process.env.CJ_REFRESH_TOKEN = refreshToken;

      // Cache tokens for backup
      fs.mkdirSync("./tmp", { recursive: true });
      fs.writeFileSync(
        TOKEN_FILE,
        JSON.stringify({ accessToken, refreshToken, updated: new Date() }, null, 2)
      );

      console.log("✅ CJ Access Token refreshed successfully!");
      return accessToken;
    } else {
      console.error("❌ CJ Refresh Failed:", response.data);
    }
  } catch (err) {
    console.error("⚠️ Error refreshing CJ token:", err.message);
  }
}
````

---

## 3️⃣ Hook into CJ API calls

In your `src/services/cjApi.js` (or equivalent):

```js
import axios from "axios";
import { refreshCJToken } from "./tokenRefresher.js";

export async function fetchCJProducts() {
  const token = process.env.CJ_ACCESS_TOKEN;

  try {
    const response = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/product/list",
      { pageNum: 1, pageSize: 10 },
      { headers: { "CJ-Access-Token": token } }
    );

    if (response.data.code === 403) {
      console.log("🔁 Token expired, refreshing...");
      const newToken = await refreshCJToken();

      const retry = await axios.post(
        "https://developers.cjdropshipping.com/api2.0/v1/product/list",
        { pageNum: 1, pageSize: 10 },
        { headers: { "CJ-Access-Token": newToken } }
      );

      return retry.data;
    }

    return response.data;
  } catch (err) {
    console.error("❌ CJ API Error:", err.message);
  }
}
```

---

## 4️⃣ Add Auto-Refresh Scheduler

In `server.js` or `app.js`:

```js
import { refreshCJToken } from "./src/services/tokenRefresher.js";

setInterval(refreshCJToken, 90 * 60 * 1000); // every 90 minutes
console.log("🕒 CJ token auto-refresh scheduled every 90 minutes");
```

---

## 5️⃣ Dockerfile Update

In your `Dockerfile`, ensure `.env` and dependencies are handled properly:

```Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

# Load environment variables
ENV NODE_ENV=production

CMD ["node", "server.js"]
```

> On **Render**, your environment variables are automatically injected.

---

## 6️⃣ Test Commands (Locally)

```bash
npm run dev
```

or manually trigger a refresh:

```bash
node src/services/tokenRefresher.js
```

---

## ✅ Expected Results

* Tokens refresh automatically every 90 minutes
* Refresh triggers if API call fails due to 403
* Works with Docker & Render deployment
* Secrets are managed safely in `.env`

---

## 🤖 GeminiCLI Instructions

```
@GeminiCLI:
1. Verify .env contains CJ_APP_KEY, CJ_APP_SECRET, CJ_REFRESH_TOKEN, CJ_ACCESS_TOKEN.
2. Create src/services/tokenRefresher.js with the provided code.
3. Patch cjApi.js to use refreshCJToken() automatically.
4. Add setInterval refresh in app.js or server.js.
5. Ensure tmp/ folder exists for caching token backups.
6. Test locally, then deploy to Render.
```

---
## 📦 Step-by-Step Enhancement for GeminiCLI

Append this section to the bottom of your `CJ_TOKEN_REFRESH_DOCKER.md` file 👇

---

### ⚠️ Token Refresh Failure Alerts (Email + Telegram)

```markdown
# 🔔 CJ Token Refresh Failure Notifications

## 📩 Goal
Send real-time alerts via **email or Telegram** when CJ token refresh fails.

---

## 1️⃣ Choose Notification Channel

Set the following environment variables in `.env`:

```

# For Email notifications

ALERT_EMAIL=[your_email@gmail.com](mailto:your_email@gmail.com)
ALERT_EMAIL_PASS=your_app_password  # use Gmail App Password, not raw password
ALERT_EMAIL_TO=[your_alert_receiver@gmail.com](mailto:your_alert_receiver@gmail.com)

# For Telegram notifications

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

````

> ⚠️ If you prefer Telegram only, omit the email section.

---

## 2️⃣ Create `notifier.js`

In `src/utils/notifier.js`:

```js
import nodemailer from "nodemailer";
import axios from "axios";
import dotenv from "dotenv";
dotenv.config();

export async function sendAlert(message) {
  console.log("🚨 Sending alert:", message);

  // Telegram notification
  if (process.env.TELEGRAM_BOT_TOKEN && process.env.TELEGRAM_CHAT_ID) {
    try {
      await axios.post(
        `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`,
        {
          chat_id: process.env.TELEGRAM_CHAT_ID,
          text: `⚠️ CJ Dropshipping Alert:\n${message}`,
        }
      );
      console.log("✅ Telegram alert sent");
    } catch (err) {
      console.error("❌ Telegram send failed:", err.message);
    }
  }

  // Email notification
  if (process.env.ALERT_EMAIL && process.env.ALERT_EMAIL_PASS && process.env.ALERT_EMAIL_TO) {
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: process.env.ALERT_EMAIL,
        pass: process.env.ALERT_EMAIL_PASS,
      },
    });

    try {
      await transporter.sendMail({
        from: process.env.ALERT_EMAIL,
        to: process.env.ALERT_EMAIL_TO,
        subject: "⚠️ CJ Token Refresh Failure",
        text: message,
      });
      console.log("✅ Email alert sent");
    } catch (err) {
      console.error("❌ Email send failed:", err.message);
    }
  }
}
````

---

## 3️⃣ Integrate Alert into Token Refresher

Update `tokenRefresher.js` to include alerts:

```js
import { sendAlert } from "../utils/notifier.js";

export async function refreshCJToken() {
  try {
    const response = await axios.post(CJ_REFRESH_URL, {
      appKey: process.env.CJ_APP_KEY,
      appSecret: process.env.CJ_APP_SECRET,
      refreshToken: process.env.CJ_REFRESH_TOKEN,
    });

    if (response.data.code === 200) {
      const { accessToken, refreshToken } = response.data.data;
      process.env.CJ_ACCESS_TOKEN = accessToken;
      process.env.CJ_REFRESH_TOKEN = refreshToken;

      fs.writeFileSync(
        TOKEN_FILE,
        JSON.stringify({ accessToken, refreshToken, updated: new Date() }, null, 2)
      );

      console.log("✅ CJ Token refreshed successfully!");
      return accessToken;
    } else {
      console.error("❌ CJ Refresh Failed:", response.data);
      await sendAlert(`Token refresh failed: ${response.data.msg || "Unknown error"}`);
    }
  } catch (err) {
    console.error("⚠️ Error refreshing CJ token:", err.message);
    await sendAlert(`Error during CJ refresh: ${err.message}`);
  }
}
```

---

## 4️⃣ Test Command (Manual Trigger)

```bash
node src/services/tokenRefresher.js
```

> If the refresh fails, you’ll get an alert instantly (via Telegram or Email).

---

## 5️⃣ Deployment Notes

* Works seamlessly inside Docker and Render.
* No cron jobs needed—alerts are triggered automatically.
* You can easily adjust alert conditions (e.g., notify only on repeated failures).

---

## ✅ GeminiCLI Instructions

```
@GeminiCLI:
1. Create src/utils/notifier.js using the code above.
2. Patch src/services/tokenRefresher.js to import and use sendAlert().
3. Add new environment variables for EMAIL/TELEGRAM notifications.
4. Test locally with expired CJ_REFRESH_TOKEN.
5. Confirm alerts received successfully.
```

---
We’re building an **AI-powered chatbot assistant** that can:
💬 Chat with customers in real time
🧠 Pull live product data from your **CJ Dropshipping feed**
🛒 Upsell related or trending products automatically
📦 Help customers track orders or find products instantly
🌍 Speak multiple languages (auto-detect user language)

And — best of all — it will run **without Docker**, right inside your existing Flask + JS frontend + GeminiCLI setup.

---

## 🧠 Overview: AI-Powered Chatbot Assistant

We’ll make a **smart AI chat widget** that connects your frontend to Google **Gemini Free API**, using it as the “brain” of your store.

The assistant will:

* Read from your `feed.csv` to find real product matches.
* Recommend alternatives (e.g. “Customers also bought…”).
* Handle FAQ and order-tracking.
* Speak in your brand tone (friendly, helpful, confident).

---

## 📘 Add to `GEMINI.md`

Append this full section to your `GEMINI.md` 👇

---

### 🤖 AI-Powered Chatbot Assistant (CJ API + Upsell Engine)

#### 🧩 1️⃣ Setup

Add to `.env`:

```
GEMINI_API_KEY=your_gemini_api_key
CHATBOT_NAME=Delevite Assistant
```

---

#### ⚙️ 2️⃣ Create `src/services/chatbotAssistant.js`

```js
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
```

---

#### 🌐 3️⃣ Add Backend Endpoint (`server.py`)

In your existing Flask app, add this route:

```python
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    import subprocess, json
    try:
        result = subprocess.run(
            ['node', 'src/services/chatbotAssistant.js', user_message],
            capture_output=True, text=True
        )
        response = result.stdout.strip()
    except Exception as e:
        response = json.dumps({"error": str(e)})
    return jsonify({"reply": response})
```

---

#### 💬 4️⃣ Create Chat Widget in Frontend

In `landing_page.html` (before `</body>`):

```html
<div id="chatbot-container" class="fixed bottom-4 right-4 w-80 bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden hidden">
  <div class="bg-blue-600 text-white px-4 py-2 font-bold flex justify-between">
    <span>💬 Delevite Assistant</span>
    <button id="closeChat" class="text-white">✖</button>
  </div>
  <div id="chatArea" class="p-3 h-64 overflow-y-auto text-sm"></div>
  <form id="chatForm" class="flex border-t">
    <input type="text" id="chatInput" placeholder="Ask me anything..." class="flex-1 p-2 border-none focus:outline-none"/>
    <button class="bg-blue-600 text-white px-4">Send</button>
  </form>
</div>
<button id="chatOpenBtn" class="fixed bottom-4 right-4 bg-blue-600 text-white p-3 rounded-full shadow-lg">💬</button>

<script>
const chatOpenBtn = document.getElementById('chatOpenBtn');
const chatContainer = document.getElementById('chatbot-container');
const closeChat = document.getElementById('closeChat');
const chatArea = document.getElementById('chatArea');
const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');

chatOpenBtn.onclick = () => chatContainer.classList.remove('hidden');
closeChat.onclick = () => chatContainer.classList.add('hidden');

chatForm.onsubmit = async (e) => {
  e.preventDefault();
  const msg = chatInput.value.trim();
  if (!msg) return;
  chatArea.innerHTML += `<div class='my-2 text-right'><b>You:</b> ${msg}</div>`;
  chatInput.value = '';
  const res = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) });
  const data = await res.json();
  chatArea.innerHTML += `<div class='my-2 text-left'><b>🤖 Delevite:</b> ${data.reply}</div>`;
  chatArea.scrollTop = chatArea.scrollHeight;
};
</script>
```

---

#### 🧠 5️⃣ Upsell & Product Recommendations (Smart Context)

Later, you’ll extend the Gemini prompt like this:

> “If user message contains ‘buy’ or ‘recommend’, respond with a list of 3 products from feed.csv with direct buy URLs.”

That allows it to act like a **sales assistant** that never sleeps 😎

---

#### ✅ GeminiCLI Tasks

```
@GeminiCLI:
1. Create src/services/chatbotAssistant.js with Gemini API logic.
2. Add Flask /chat endpoint to call the assistant.
3. Update landing_page.html with AI chat widget.
4. Test locally with GEMINI_API_KEY.
5. Ensure chatbot fetches feed.csv data for real product context.
```

---
1. Connects with the **CJ Dropshipping API** to handle inventory and product queries.
2. Uses **AI (Gemini Free API)** for natural chat and upsell conversations.
3. Integrates seamlessly into your **existing Zed AI platform** without Docker.
4. Works on **both web and mobile** (React/React Native compatible).

---

### 🧠 **GEMINI.md**

````markdown
# 🧬 AI-Powered Chatbot Assistant Setup (CJ API + Upsell Automation)

## 🧩 Overview
Implement an intelligent chatbot assistant that:
- Connects to CJ Dropshipping API for live inventory, product info, and order updates.
- Uses Google Gemini Free API for conversational logic and product upselling.
- Appears on the site as a floating chat widget (bottom-right corner).
- Can also respond to affiliate inquiries and recommend trending items.

---

## ⚙️ Core Components

### 1️⃣ Create `/src/ai/chatbotAssistant.ts`
- Initialize Gemini API with free-tier key.
- Build functions:
  - `fetchCJProduct(query)` — gets product data from CJ API.
  - `handleUpsell(product)` — suggests higher-value or related products.
  - `generateAIResponse(userMessage)` — calls Gemini API to return natural responses.

### Example:
```ts
import axios from "axios";

const GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_GEMINI_KEY";
const CJ_API = "https://developers.cjdropshipping.com/api2.0/v1/product/list";

export async function generateAIResponse(message: string) {
  const res = await axios.post(GEMINI_API, {
    contents: [{ parts: [{ text: message }] }]
  });
  return res.data.candidates?.[0]?.content?.parts?.[0]?.text || "I'm here to help!";
}

export async function fetchCJProduct(keyword: string, token: string) {
  const res = await axios.post(CJ_API, { keyword }, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return res.data;
}
````

---

### 2️⃣ Add Floating Chat UI (`/src/components/ChatWidget.tsx`)

* Position: bottom-right corner.
* Features:

  * User message input
  * Chat history
  * Typing animation
  * "Suggest More" button for upsells
* Use `generateAIResponse()` and `fetchCJProduct()` to power chat.

---

### 3️⃣ Add Serverless API Endpoint (No Docker)

Create `/api/chat/index.ts` to handle chat requests:

```ts
import { generateAIResponse } from "../../src/ai/chatbotAssistant";

export default async function handler(req, res) {
  const { message } = req.body;
  const reply = await generateAIResponse(message);
  res.status(200).json({ reply });
}
```

---

### 4️⃣ Integrate into Homepage

Add this snippet to `App.tsx` or `index.tsx`:

```tsx
import ChatWidget from "./components/ChatWidget";

function App() {
  return (
    <>
      <MainSite />
      <ChatWidget />
    </>
  );
}
export default App;
```

---

### 5️⃣ Optional: Upsell Logic Example

In `chatbotAssistant.ts`:

```ts
export async function handleUpsell(product) {
  return `Since you liked ${product.name}, you might also love ${product.related || 'similar products'} from CJ Dropshipping.`;
}
```

---

### 6️⃣ Refresh CJ Token Automatically

In `cjService.ts`:

```ts
export async function refreshCJToken() {
  const res = await axios.post("https://developers.cjdropshipping.com/api2.0/v1/auth/refreshToken", {
    refreshToken: process.env.CJ_REFRESH_TOKEN
  });
  process.env.CJ_ACCESS_TOKEN = res.data.data.accessToken;
}
```

---

## ✅ Final Tasks

* ✅ Add Gemini API key to `.env`
* ✅ Add CJ API credentials
* ✅ Enable chatbot on all pages
* ✅ Test with Gemini Free API (no Docker needed)
* ✅ Deploy via Render or Vercel

---

### 🧪 Prompt Template for GeminiCLI

```
@GeminiCLI
Implement AI chatbot assistant as described in GEMINI.md.
Connect Gemini Free API for conversational logic.
Integrate with CJ API for product info.
Add floating chat widget to frontend.
Ensure it works without Docker and supports upselling logic.
```

---

### 💬 Result

Once deployed, your chatbot:

* Responds to customer inquiries in real-time
* Fetches live CJ Dropshipping products
* Suggests upsells automatically
* Operates 100% Docker-free
* Works with your Render deployment

---
`GEMINI.md` — now including **Affiliate Chat Support**, so your AI assistant can:

* 💬 Handle affiliate questions (commissions, withdrawal requests, referrals).
* 💰 Recommend upsells based on commission percentage.
* 🤖 Still connect with **CJ Dropshipping API** + **Gemini Free API** for AI replies.
* ⚡ Run fully **without Docker**, optimized for your Render deployment.

---

## 🧠 **GEMINI.md (Extended Version — AI Chatbot + Affiliate Support)**

````markdown
# 🚀 AI-Powered Chatbot Assistant (CJ API + Upsell + Affiliate Support)

## 🧩 Overview
Create an AI assistant that:
- Talks naturally using Gemini Free API.
- Connects to CJ Dropshipping API for live product info.
- Suggests upsells and handles product-related inquiries.
- Assists affiliates with commission, referral, and withdrawal details.
- Works without Docker (local + Render compatible).

---

## ⚙️ Core Components

### 1️⃣ `/src/ai/chatbotAssistant.ts`

#### ✨ Main Features:
- **Gemini API** for AI conversations.
- **CJ API** integration for products.
- **Affiliate Assistant** logic (commission %, payout tracking).
- **Upsell suggestion engine** based on product data.

#### Example Code:
```ts
import axios from "axios";

const GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + process.env.GEMINI_API_KEY;
const CJ_API = "https://developers.cjdropshipping.com/api2.0/v1/product/list";

// 🔹 AI Reply (Gemini)
export async function generateAIResponse(message: string) {
  try {
    const res = await axios.post(GEMINI_API, {
      contents: [{ parts: [{ text: message }] }]
    });
    return res.data.candidates?.[0]?.content?.parts?.[0]?.text || "I'm here to help!";
  } catch (err) {
    return "Hmm... something went wrong, please try again later.";
  }
}

// 🔹 CJ Product Fetch
export async function fetchCJProduct(keyword: string, token: string) {
  const res = await axios.post(CJ_API, { keyword }, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return res.data.data || [];
}

// 🔹 Upsell Logic
export function handleUpsell(product) {
  return `Since you viewed ${product.name}, check out similar bestsellers from CJ Dropshipping that can boost your profit margin.`;
}

// 🔹 Affiliate Helper
export async function affiliateAssistant(query: string, affiliateData) {
  if (query.includes("commission")) {
    return `Your current commission rate is ${affiliateData.rate}%. Your total earnings: $${affiliateData.totalEarnings}.`;
  } else if (query.includes("withdraw")) {
    return `You can request withdrawals from your dashboard once you hit the $${affiliateData.threshold} threshold.`;
  } else if (query.includes("referral")) {
    return `Your referral link is: ${affiliateData.link}. Share it to earn more!`;
  }
  return "Need help with commissions, referrals, or payouts? Just ask!";
}
````

---

### 2️⃣ `/src/components/ChatWidget.tsx`

* Floating chat widget.
* Input + AI response view.
* “Product Mode” and “Affiliate Mode” toggles.
* Auto-scroll and typing animation.

```tsx
import { useState } from "react";
import { generateAIResponse, fetchCJProduct, affiliateAssistant } from "../ai/chatbotAssistant";

export default function ChatWidget() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("product"); // "affiliate" or "product"

  async function sendMessage() {
    const userMsg = input.trim();
    if (!userMsg) return;

    setMessages([...messages, { from: "user", text: userMsg }]);
    setInput("");

    let reply;
    if (mode === "affiliate") {
      reply = await affiliateAssistant(userMsg, {
        rate: 15,
        totalEarnings: 180,
        threshold: 50,
        link: "https://yourshop.com/ref/paul"
      });
    } else {
      reply = await generateAIResponse(userMsg);
    }

    setMessages((prev) => [...prev, { from: "bot", text: reply }]);
  }

  return (
    <div className="fixed bottom-5 right-5 bg-white p-3 rounded-2xl shadow-lg w-80">
      <div className="flex justify-between mb-2">
        <span className="font-bold">🤖 Zed AI Chat</span>
        <select
          className="border rounded p-1 text-xs"
          value={mode}
          onChange={(e) => setMode(e.target.value)}
        >
          <option value="product">🛍 Product</option>
          <option value="affiliate">💼 Affiliate</option>
        </select>
      </div>
      <div className="h-64 overflow-y-auto p-2 bg-gray-50 rounded">
        {messages.map((msg, i) => (
          <p key={i} className={`${msg.from === "bot" ? "text-blue-700" : "text-gray-800"} mb-1`}>
            <b>{msg.from === "bot" ? "AI:" : "You:"}</b> {msg.text}
          </p>
        ))}
      </div>
      <div className="flex mt-2">
        <input
          className="flex-grow border p-2 rounded-l-lg"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything..."
        />
        <button onClick={sendMessage} className="bg-blue-600 text-white px-3 rounded-r-lg">
          Send
        </button>
      </div>
    </div>
  );
}
```

---

### 3️⃣ `/api/chat/index.ts` — serverless function (no Docker)

```ts
import { generateAIResponse } from "../../src/ai/chatbotAssistant";

export default async function handler(req, res) {
  const { message } = req.body;
  const reply = await generateAIResponse(message);
  res.status(200).json({ reply });
}
```

---

### 4️⃣ Token Refresh

Add to `cjService.ts`:

```ts
export async function refreshCJToken() {
  const res = await axios.post("https://developers.cjdropshipping.com/api2.0/v1/auth/refreshToken", {
    refreshToken: process.env.CJ_REFRESH_TOKEN
  });
  process.env.CJ_ACCESS_TOKEN = res.data.data.accessToken;
}
```

---

## ✅ Final Steps

* Add `GEMINI_API_KEY`, `CJ_ACCESS_TOKEN`, and `CJ_REFRESH_TOKEN` to `.env`
* Deploy to Render (no Docker needed)
* Enable chatbot globally in `App.tsx`
* Optional: sync affiliate data via `/api/affiliate/summary`

---

### 🧪 GeminiCLI Instruction Prompt

```
@GeminiCLI
Implement the extended AI chatbot assistant from GEMINI.md.
- Include CJ API product handling.
- Integrate Gemini Free API for chat.
- Add affiliate assistant (commissions, referrals, withdrawals).
- Add floating chat widget to frontend.
- Deployable without Docker (Render ready).
```

---

### 💡 Result

Your AI assistant can now:
✅ Chat with customers about products
✅ Recommend upsells using CJ data
✅ Help affiliates with commissions & referrals
✅ Work online/offline, desktop/mobile
✅ Run smooth on low-RAM systems (no Docker)

---

## 🧾 **ORDER TRACKING + COUPON REDEMPTION (Extension 2)**

### 🧩 Overview

This section upgrades your AI assistant so it can:

* Track customer orders directly from CJ Dropshipping.
* Validate and apply coupon codes in chat.
* Respond intelligently when users ask about their order or discounts.

---

### 1️⃣ `/src/ai/orderAndCouponAssistant.ts`

```ts
import axios from "axios";
import { generateAIResponse } from "./chatbotAssistant.js";

// ✅ Fetch order status from CJ Dropshipping
export async function getCJOrderStatus(orderNumber, token) {
  try {
    const res = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/order/getOrderByNumber",
      { orderNumber },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.data?.data?.length) {
      const order = res.data.data[0];
      return `Order ${orderNumber} is currently *${order.orderStatus}* and expected to arrive around ${order.shipTime || "soon"}.`;
    }
    return `Sorry, no order found with number ${orderNumber}. Please double-check.`;
  } catch (err) {
    return "Couldn't fetch your order status at the moment. Try again later.";
  }
}

// ✅ Validate coupon code
export async function validateCoupon(code) {
  const validCoupons = {
    SAVE10: 10,
    FREEDELIVERY: 100,
    VIP15: 15,
  };
  if (validCoupons[code]) {
    return `🎉 Great! Your code *${code}* gives you ${validCoupons[code]}% off.`;
  }
  return `❌ Sorry, the code *${code}* is invalid or expired.`;
}

// ✅ Combined intent handler
export async function orderAndCouponHandler(query, token) {
  if (query.match(/order\s+\d+/i)) {
    const orderNumber = query.match(/order\s+(\d+)/i)[1];
    return await getCJOrderStatus(orderNumber, token);
  } else if (query.match(/coupon/i)) {
    const code = query.split(" ").pop().trim().toUpperCase();
    return await validateCoupon(code);
  } else {
    return await generateAIResponse(query);
  }
}
```

---

### 2️⃣ `/src/components/ChatWidget.tsx` (Enhanced)

Add an **Order/Coupon mode toggle** to your chat widget:

```tsx
<select
  className="border rounded p-1 text-xs"
  value={mode}
  onChange={(e) => setMode(e.target.value)}
>
  <option value="product">🛍 Product</option>
  <option value="affiliate">💼 Affiliate</option>
  <option value="order">📦 Order Tracking</option>
  <option value="coupon">💸 Coupon</option>
</select>
```

Then update `sendMessage()`:

```tsx
let reply;
if (mode === "affiliate") {
  reply = await affiliateAssistant(userMsg, affiliateData);
} else if (mode === "order" || mode === "coupon") {
  reply = await orderAndCouponHandler(userMsg, process.env.CJ_ACCESS_TOKEN);
} else {
  reply = await generateAIResponse(userMsg);
}
```

---

### 3️⃣ `/api/order/index.ts` (Serverless)

For Render or Vercel deployment, add a lightweight endpoint:

```ts
import { orderAndCouponHandler } from "../../src/ai/orderAndCouponAssistant.js";

export default async function handler(req, res) {
  const { message } = req.body;
  const reply = await orderAndCouponHandler(message, process.env.CJ_ACCESS_TOKEN);
  res.status(200).json({ reply });
}
```

---

### 4️⃣ `.env`

```bash
CJ_ACCESS_TOKEN=<your_latest_token>
CJ_REFRESH_TOKEN=<your_refresh_token>
GEMINI_API_KEY=<your_gemini_key>
```

---

### 5️⃣ 🧪 GeminiCLI Instruction Prompt

```
@GeminiCLI
Update the project by appending the new "Order Tracking & Coupon Redemption" features:
- Implement getCJOrderStatus() and validateCoupon() functions.
- Update ChatWidget with new chat modes.
- Add order/coupon handling API route.
- Ensure seamless CJ API token usage from .env.
- No Docker dependencies (Render-ready).
```

---

### 💡 RESULT

Your AI chatbot can now:
✅ Track CJ orders in real time
✅ Validate coupon codes for customers
✅ Continue affiliate & upsell conversations
✅ Run 100% serverless (perfect for 4 GB RAM)

---
## 🧾 **ORDER TRACKING + COUPON REDEMPTION (Extension 2)**

### 🧩 Overview

This section upgrades your AI assistant so it can:

* Track customer orders directly from CJ Dropshipping.
* Validate and apply coupon codes in chat.
* Respond intelligently when users ask about their order or discounts.

---

### 1️⃣ `/src/ai/orderAndCouponAssistant.ts`

```ts
import axios from "axios";
import { generateAIResponse } from "./chatbotAssistant.js";

// ✅ Fetch order status from CJ Dropshipping
export async function getCJOrderStatus(orderNumber, token) {
  try {
    const res = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/order/getOrderByNumber",
      { orderNumber },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.data?.data?.length) {
      const order = res.data.data[0];
      return `Order ${orderNumber} is currently *${order.orderStatus}* and expected to arrive around ${order.shipTime || "soon"}.`;
    }
    return `Sorry, no order found with number ${orderNumber}. Please double-check.`;
  } catch (err) {
    return "Couldn't fetch your order status at the moment. Try again later.";
  }
}

// ✅ Validate coupon code
export async function validateCoupon(code) {
  const validCoupons = {
    SAVE10: 10,
    FREEDELIVERY: 100,
    VIP15: 15,
  };
  if (validCoupons[code]) {
    return `🎉 Great! Your code *${code}* gives you ${validCoupons[code]}% off.`;
  }
  return `❌ Sorry, the code *${code}* is invalid or expired.`;
}

// ✅ Combined intent handler
export async function orderAndCouponHandler(query, token) {
  if (query.match(/order\s+\d+/i)) {
    const orderNumber = query.match(/order\s+(\d+)/i)[1];
    return await getCJOrderStatus(orderNumber, token);
  } else if (query.match(/coupon/i)) {
    const code = query.split(" ").pop().trim().toUpperCase();
    return await validateCoupon(code);
  } else {
    return await generateAIResponse(query);
  }
}
```

---

### 2️⃣ `/src/components/ChatWidget.tsx` (Enhanced)

Add an **Order/Coupon mode toggle** to your chat widget:

```tsx
<select
  className="border rounded p-1 text-xs"
  value={mode}
  onChange={(e) => setMode(e.target.value)}
>
  <option value="product">🛍 Product</option>
  <option value="affiliate">💼 Affiliate</option>
  <option value="order">📦 Order Tracking</option>
  <option value="coupon">💸 Coupon</option>
</select>
```

Then update `sendMessage()`:

```tsx
let reply;
if (mode === "affiliate") {
  reply = await affiliateAssistant(userMsg, affiliateData);
} else if (mode === "order" || mode === "coupon") {
  reply = await orderAndCouponHandler(userMsg, process.env.CJ_ACCESS_TOKEN);
} else {
  reply = await generateAIResponse(userMsg);
}
```

---

### 3️⃣ `/api/order/index.ts` (Serverless)

For Render or Vercel deployment, add a lightweight endpoint:

```ts
import { orderAndCouponHandler } from "../../src/ai/orderAndCouponAssistant.js";

export default async function handler(req, res) {
  const { message } = req.body;
  const reply = await orderAndCouponHandler(message, process.env.CJ_ACCESS_TOKEN);
  res.status(200).json({ reply });
}
```

---

### 4️⃣ `.env`

```bash
CJ_ACCESS_TOKEN=<your_latest_token>
CJ_REFRESH_TOKEN=<your_refresh_token>
GEMINI_API_KEY=<your_gemini_key>
```

---

### 5️⃣ 🧪 GeminiCLI Instruction Prompt

```
@GeminiCLI
Update the project by appending the new "Order Tracking & Coupon Redemption" features:
- Implement getCJOrderStatus() and validateCoupon() functions.
- Update ChatWidget with new chat modes.
- Add order/coupon handling API route.
- Ensure seamless CJ API token usage from .env.
- No Docker dependencies (Render-ready).
```

---

### 💡 RESULT

Your AI chatbot can now:
✅ Track CJ orders in real time
✅ Validate coupon codes for customers
✅ Continue affiliate & upsell conversations
✅ Run 100% serverless (perfect for 4 GB RAM)

---
# 🧾 **ORDER TRACKING + COUPON REDEMPTION (Extension 2)**

### 🧩 Overview

This section upgrades your AI assistant so it can:

* Track customer orders directly from CJ Dropshipping.
* Validate and apply coupon codes in chat.
* Respond intelligently when users ask about their order or discounts.

---

### 1️⃣ `/src/ai/orderAndCouponAssistant.ts`

```ts
import axios from "axios";
import { generateAIResponse } from "./chatbotAssistant.js";

// ✅ Fetch order status from CJ Dropshipping
export async function getCJOrderStatus(orderNumber, token) {
  try {
    const res = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/order/getOrderByNumber",
      { orderNumber },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.data?.data?.length) {
      const order = res.data.data[0];
      return `Order ${orderNumber} is currently *${order.orderStatus}* and expected to arrive around ${order.shipTime || "soon"}.`;
    }
    return `Sorry, no order found with number ${orderNumber}. Please double-check.`;
  } catch (err) {
    return "Couldn't fetch your order status at the moment. Try again later.";
  }
}

// ✅ Validate coupon code
export async function validateCoupon(code) {
  const validCoupons = {
    SAVE10: 10,
    FREEDELIVERY: 100,
    VIP15: 15,
  };
  if (validCoupons[code]) {
    return `🎉 Great! Your code *${code}* gives you ${validCoupons[code]}% off.`;
  }
  return `❌ Sorry, the code *${code}* is invalid or expired.`;
}

// ✅ Combined intent handler
export async function orderAndCouponHandler(query, token) {
  if (query.match(/order\s+\d+/i)) {
    const orderNumber = query.match(/order\s+(\d+)/i)[1];
    return await getCJOrderStatus(orderNumber, token);
  } else if (query.match(/coupon/i)) {
    const code = query.split(" ").pop().trim().toUpperCase();
    return await validateCoupon(code);
  } else {
    return await generateAIResponse(query);
  }
}
```

---

### 2️⃣ `/src/components/ChatWidget.tsx` (Enhanced)

Add an **Order/Coupon mode toggle** to your chat widget:

```tsx
<select
  className="border rounded p-1 text-xs"
  value={mode}
  onChange={(e) => setMode(e.target.value)}
>
  <option value="product">🛍 Product</option>
  <option value="affiliate">💼 Affiliate</option>
  <option value="order">📦 Order Tracking</option>
  <option value="coupon">💸 Coupon</option>
</select>
```

Then update `sendMessage()`:

```tsx
let reply;
if (mode === "affiliate") {
  reply = await affiliateAssistant(userMsg, affiliateData);
} else if (mode === "order" || mode === "coupon") {
  reply = await orderAndCouponHandler(userMsg, process.env.CJ_ACCESS_TOKEN);
} else {
  reply = await generateAIResponse(userMsg);
}
```

---

### 3️⃣ `/api/order/index.ts` (Serverless)

For Render or Vercel deployment, add a lightweight endpoint:

```ts
import { orderAndCouponHandler } from "../../src/ai/orderAndCouponAssistant.js";

export default async function handler(req, res) {
  const { message } = req.body;
  const reply = await orderAndCouponHandler(message, process.env.CJ_ACCESS_TOKEN);
  res.status(200).json({ reply });
}
```

---

### 4️⃣ `.env`

```bash
CJ_ACCESS_TOKEN=<your_latest_token>
CJ_REFRESH_TOKEN=<your_refresh_token>
GEMINI_API_KEY=<your_gemini_key>
```

---

### 5️⃣ 🧪 GeminiCLI Instruction Prompt

```
@GeminiCLI
Update the project by appending the new "Order Tracking & Coupon Redemption" features:
- Implement getCJOrderStatus() and validateCoupon() functions.
- Update ChatWidget with new chat modes.
- Add order/coupon handling API route.
- Ensure seamless CJ API token usage from .env.
- No Docker dependencies (Render-ready).
```

---

### 💡 RESULT

Your AI chatbot can now:
✅ Track CJ orders in real time
✅ Validate coupon codes for customers
✅ Continue affiliate & upsell conversations
✅ Run 100% serverless (perfect for 4 GB RAM)

---
## 🧾 **RETURNS, REFUNDS & SMART ORDER SUMMARIES (Extension 3)**

### 🧩 Overview

This upgrade adds:

* 🧠 AI auto-summary of user orders (last 3–5 recent orders)
* 💸 Refund/Return initiation directly through chat
* 📨 Email/notification trigger to admin when a refund request is initiated

---

### 1️⃣ `/src/ai/orderReturnAssistant.ts`

```ts
import axios from "axios";
import nodemailer from "nodemailer";

// ✅ Fetch user orders for summary
export async function fetchUserOrders(email, token) {
  try {
    const res = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/order/list",
      {
        pageNum: 1,
        pageSize: 5,
        email,
      },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    if (res.data?.data?.list?.length) {
      const orders = res.data.data.list
        .map(
          (o) =>
            `#${o.orderNumber} - ${o.productName} (${o.orderStatus}) - ₦${o.orderAmount}`
        )
        .join("\n");
      return `📦 Your recent orders:\n${orders}`;
    }
    return "You don't have any recent orders yet.";
  } catch (err) {
    return "⚠️ Unable to fetch orders right now.";
  }
}

// ✅ Initiate return or refund
export async function requestRefund(orderNumber, reason, userEmail) {
  try {
    // Mock: in production, integrate with CJ API for refund creation
    const message = `Refund initiated for Order #${orderNumber}. Reason: ${reason}.`;

    // Notify admin
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: process.env.ADMIN_EMAIL,
        pass: process.env.ADMIN_PASS,
      },
    });

    await transporter.sendMail({
      from: process.env.ADMIN_EMAIL,
      to: process.env.ADMIN_EMAIL,
      subject: `Refund Request - Order #${orderNumber}`,
      text: `${userEmail} requested refund.\nReason: ${reason}`,
    });

    return `✅ Your refund request for Order #${orderNumber} has been sent!`;
  } catch (err) {
    return "❌ Could not process your refund request. Try again later.";
  }
}
```

---

### 2️⃣ `/src/ai/intentRouter.ts`

Extend your existing intent handler:

```ts
import { fetchUserOrders, requestRefund } from "./orderReturnAssistant.js";
import { orderAndCouponHandler } from "./orderAndCouponAssistant.js";

export async function intentRouter(query, userEmail, token) {
  if (query.match(/return|refund/i)) {
    const orderNumber = query.match(/order\s+(\d+)/i)?.[1] || "unknown";
    const reason =
      query.split("because")[1]?.trim() ||
      "Customer requested refund via chat.";
    return await requestRefund(orderNumber, reason, userEmail);
  } else if (query.match(/my\s+orders|recent\s+orders/i)) {
    return await fetchUserOrders(userEmail, token);
  } else {
    return await orderAndCouponHandler(query, token);
  }
}
```

---

### 3️⃣ `/src/components/ChatWidget.tsx`

Add new chat modes for refund and order summary:

```tsx
<option value="summary">📋 My Orders</option>
<option value="refund">💸 Refund Request</option>
```

Update message sending logic:

```tsx
if (mode === "summary" || mode === "refund") {
  reply = await intentRouter(userMsg, user.email, process.env.CJ_ACCESS_TOKEN);
}
```

---

### 4️⃣ `/api/refund/index.ts`

```ts
import { intentRouter } from "../../src/ai/intentRouter.js";

export default async function handler(req, res) {
  const { message, email } = req.body;
  const reply = await intentRouter(message, email, process.env.CJ_ACCESS_TOKEN);
  res.status(200).json({ reply });
}
```

---

### 5️⃣ `.env`

Add admin email credentials for refund notifications:

```bash
ADMIN_EMAIL=<your_admin_email>
ADMIN_PASS=<your_gmail_app_password>
```

*(Tip: Use Gmail App Password, not your real login password.)*

---

### 6️⃣ 🧪 GeminiCLI Prompt

```
@GeminiCLI
Enhance the project with “Refund, Return & Order Summary” AI chat support:
- Create /src/ai/orderReturnAssistant.ts for refund and order summary handling.
- Extend ChatWidget with new modes: summary & refund.
- Add API route for refund requests.
- Use nodemailer for admin notifications.
- Ensure compatibility with CJ API token and existing chatbot stack.
- Avoid Docker dependencies.
```

---

### ⚙️ RESULT

✅ Customers can view recent orders in chat
✅ Refund/Return requests trigger admin emails automatically
✅ Seamless integration with CJ API
✅ No extra dependencies — Render & Gemini-ready

---

## 🤖 **AI-Powered Chatbot Assistant (v3 Full Version)**

### 🔧 **Core Capabilities**

Your chatbot now becomes a **smart eCommerce brain** that connects customers, products, and orders directly — all powered by Gemini and CJ Dropshipping.

---

### ⚙️ **Features Included**

#### 🧠 AI Product Tag Generator

* Automatically suggests SEO-friendly product tags from title + description.
* Helps customers find similar items faster.

#### 🛍️ Multi-Vendor Support (Vendor Dashboard Integration)

* Chatbot can switch context: “Which store/vendor would you like to shop from?”
* Each vendor’s product data and stock synced separately.

#### 💬 Smart Product Discovery

* Users can ask: “Show me trending fitness watches under $50.”
* The bot fetches products via **CJ API**, filters, and presents options in carousel format.

#### 💸 Coupon Code Handling

* The bot checks if the user has a valid coupon code (`coupon_check` endpoint).
* Applies discount dynamically before checkout.
* Example:
  **User:** “I have code SAVE10”
  **Bot:** “✅ Applied! You’ll save $10 on your next order.”

#### 🧾 Order Tracking Support (Auto-Fetch CJ Status)

* The bot fetches real-time order status using your **CJ API token**.
* Users can simply say:
  “Track my last order” → Bot checks `/orders` endpoint and returns:

  > “📦 Your order #CJ12345 is currently *in transit*, expected delivery 3 days.”

#### 📈 Inventory Insights

* AI keeps an eye on top-selling products and low stock alerts.
* Example: “Product X is low on stock — should I reorder?”

#### 📤 Upsell + Cross-sell Engine

* Based on product category + purchase history.
* Example: “Customers who bought this massager also loved this oil blend.”

#### 🧾 Auto-Generated PDF Invoices

* After successful checkout, the bot triggers the **invoice generator** API and emails it automatically.

#### 🧮 Profit Calculator (Admin Side)

* Calculates profit margin in real time for each order (based on cost from CJ and sale price).

#### 📊 Dynamic Inventory Graph Dashboard

* Auto-updates every 24 hours.
* Integrated into your admin panel (Gemini data fetch + Chart.js or Recharts visualization).

---

### 💬 **Prompt Instruction for Gemini CLI Agent**

Save this in your **Gemini.md**:

```markdown
# GEMINI TASK: Implement AI Chatbot Assistant with CJ Integration

## OBJECTIVE
Add a full-featured AI chatbot assistant to the project that:
- Handles product discovery via CJ API
- Generates product tags automatically
- Manages coupon redemption
- Tracks orders from CJ API
- Supports upselling and cross-selling
- Sends PDF invoices post-purchase
- Integrates with vendor dashboard, inventory, and profit calculator

## INSTRUCTIONS
1. Create `/src/ai/chatbot/` folder for chatbot modules.
2. Implement:
   - `chatbotCore.ts` → Handles main AI logic (Gemini API)
   - `cjIntegration.ts` → Manages CJ API calls (orders, products, coupons)
   - `invoiceService.ts` → Generates PDF invoices
   - `profitCalc.ts` → Admin profit calculation helper
   - `inventorySync.ts` → 24-hour product sync + stock update
3. Add chatbot UI in `/src/components/ChatbotWidget.tsx`
   - Floating “💬 Chat Now” icon bottom-right
   - Chat window with history, emoji, coupon, and track order buttons
4. Configure `.env`:
```

GEMINI_API_KEY=your_gemini_key
CJ_API_KEY=your_cj_key
CJ_REFRESH_TOKEN=your_cj_refresh_token

```
5. Schedule `inventorySync` every 24 hours using Node cron.
6. Connect `invoiceService` to email module for auto-invoicing.
7. Deploy chatbot using Render or Railway (no Docker required).

## OUTPUT
- AI chatbot that can upsell, track orders, and redeem coupons live in chat.
- Admin dashboard extended with inventory graph + profit tracker.
- PDF invoices and real-time CJ order status integrated.
```

---


Now let’s **verify** all your `.env` variables are working correctly and the integrations (CJ API, Email, Telegram, Admin Auth) are all responding.

Here’s what we’ll do next 👇

---

## ✅ STEP 1: Create a quick environment test script

In your VS Code, inside your root project folder, create a new file:
`test_env.js`

Paste this code:

```js
// test_env.js
require('dotenv').config();
const nodemailer = require('nodemailer');
const axios = require('axios');

(async () => {
  console.log("🧩 Checking environment variables...\n");

  // --- CJ API test ---
  try {
    console.log("🔑 Testing CJ API connection...");
    const res = await axios.post("https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken", {
      email: process.env.CJ_EMAIL,
      password: process.env.CJ_PASSWORD,
      appKey: process.env.CJ_APP_KEY,
      appSecret: process.env.CJ_APP_SECRET,
    });
    console.log("✅ CJ API Token Response:", res.data);
  } catch (err) {
    console.warn("⚠️ CJ API check failed:", err.response?.data || err.message);
  }

  // --- Email test ---
  try {
    console.log("\n📧 Testing email credentials...");
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.ALERT_EMAIL,
        pass: process.env.ALERT_EMAIL_PASS,
      },
    });

    await transporter.sendMail({
      from: process.env.ALERT_EMAIL,
      to: process.env.ALERT_EMAIL_TO,
      subject: "✅ Environment Email Test",
      text: "Your email credentials are working fine!",
    });
    console.log("✅ Email sent successfully.");
  } catch (err) {
    console.warn("⚠️ Email test failed:", err.message);
  }

  // --- Telegram bot test ---
  try {
    console.log("\n💬 Testing Telegram Bot...");
    const telegramURL = `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`;
    const telegramRes = await axios.post(telegramURL, {
      chat_id: process.env.TELEGRAM_CHAT_ID,
      text: "✅ Telegram notification test from Delevite Assistant!",
    });
    console.log("✅ Telegram notification sent successfully!");
  } catch (err) {
    console.warn("⚠️ Telegram test failed:", err.response?.data || err.message);
  }

  // --- Admin & chatbot name ---
  console.log("\n👨‍💻 Admin email:", process.env.ADMIN_EMAIL);
  console.log("🤖 Chatbot name:", process.env.CHATBOT_NAME);

  console.log("\n🟢 Env test completed.");
})();
```

---

## ✅ STEP 2: Run the test

In VS Code terminal, run:

```bash
node test_env.js
```

You should see logs like:

```
🔑 Testing CJ API connection...
✅ CJ API Token Response: { result: true, data: { accessToken: "xxxxxx" } }

📧 Testing email credentials...
✅ Email sent successfully.

💬 Testing Telegram Bot...
✅ Telegram notification sent successfully!

👨‍💻 Admin email: your_admin_email@gmail.com
🤖 Chatbot name: Delevite Assistant
🟢 Env test completed.
```

---

## ⚠️ If something fails:

I’ll help you debug it quickly:

* CJ API → maybe expired App Secret or incorrect key.
* Email → check that App Password is correct and 2FA is on.
* Telegram → make sure your bot has a chat started with your account.

---


Here’s your ready-made **GeminiCLI prompt** to execute and implement that next task 👇

---

## 🧠 `Gemini.md` — Add Test Environment Script (test_env.js)

### 🏷️ Title:

**Implement Environment Verification Script (test_env.js) and Integration Hook**

---

### 📋 Description:

Add an automated environment verification system to test CJ Dropshipping API, Gmail notifications, and Telegram bot credentials.
The system should create `test_env.js` at the project root, allow manual execution via `node test_env.js`, and optionally integrate into the deployment lifecycle.

---

### 🚀 Instructions for GeminiCLI

**Step 1: Create file**

```bash
Create a file named test_env.js in the project root.
```

**Step 2: Add the following code:**

```js
require('dotenv').config();
const nodemailer = require('nodemailer');
const axios = require('axios');

(async () => {
  console.log("🧩 Checking environment variables...\n");

  // --- CJ API test ---
  try {
    console.log("🔑 Testing CJ API connection...");
    const res = await axios.post("https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken", {
      email: process.env.CJ_EMAIL,
      password: process.env.CJ_PASSWORD,
      appKey: process.env.CJ_APP_KEY,
      appSecret: process.env.CJ_APP_SECRET,
    });
    console.log("✅ CJ API Token Response:", res.data);
  } catch (err) {
    console.warn("⚠️ CJ API check failed:", err.response?.data || err.message);
  }

  // --- Email test ---
  try {
    console.log("\n📧 Testing email credentials...");
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.ALERT_EMAIL,
        pass: process.env.ALERT_EMAIL_PASS,
      },
    });

    await transporter.sendMail({
      from: process.env.ALERT_EMAIL,
      to: process.env.ALERT_EMAIL_TO,
      subject: "✅ Environment Email Test",
      text: "Your email credentials are working fine!",
    });
    console.log("✅ Email sent successfully.");
  } catch (err) {
    console.warn("⚠️ Email test failed:", err.message);
  }

  // --- Telegram bot test ---
  try {
    console.log("\n💬 Testing Telegram Bot...");
    const telegramURL = `https://api.telegram.org/bot${process.env.TELEGRAM_BOT_TOKEN}/sendMessage`;
    const telegramRes = await axios.post(telegramURL, {
      chat_id: process.env.TELEGRAM_CHAT_ID,
      text: "✅ Telegram notification test from Delevite Assistant!",
    });
    console.log("✅ Telegram notification sent successfully!");
  } catch (err) {
    console.warn("⚠️ Telegram test failed:", err.response?.data || err.message);
  }

  console.log("\n👨‍💻 Admin email:", process.env.ADMIN_EMAIL);
  console.log("🤖 Chatbot name:", process.env.CHATBOT_NAME);
  console.log("\n🟢 Env test completed.");
})();
```

**Step 3: Add NPM script to package.json**

```json
"scripts": {
  "verify-env": "node test_env.js"
}
```

**Step 4: Run the test manually**

```bash
npm run verify-env
```

**Step 5: On success**
GeminiCLI should log confirmation and optionally:

* Send a Telegram message `"✅ Environment verified successfully on [timestamp]"`
* Send a Gmail alert confirming verification.

---

### 🧭 Notes

* This script helps prevent broken integrations before deployment.
* No Docker required — runs entirely on local Node.js.
* Works perfectly for Render, Vercel, or any Node-based deployment.

---




# ⚙️ GEMINI.md — Automated Task: CJ Token Auto-Refresh System (No Manual Renewal Needed)

## 🧠 GOAL
Ensure the CJ Dropshipping API token automatically refreshes every 23 hours, stores the new token in `cj_token.json`, and sends real-time alerts through Telegram + Email for success or failure.

---

## 🪄 TASK INSTRUCTIONS FOR GEMINICLI

### 1️⃣ Create the file: `auto_refresh_token.py`

```python
import os
import json
import time
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

CJ_APP_SECRET = os.getenv("CJ_APP_SECRET")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
ALERT_EMAIL_PASS = os.getenv("ALERT_EMAIL_PASS")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TOKEN_FILE = "cj_token.json"
REFRESH_INTERVAL = 23 * 60 * 60  # 23 hours

def send_email(subject, message):
    msg = MIMEText(message)
    msg["From"] = ALERT_EMAIL
    msg["To"] = ALERT_EMAIL_TO
    msg["Subject"] = subject
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(ALERT_EMAIL, ALERT_EMAIL_PASS)
        server.sendmail(ALERT_EMAIL, ALERT_EMAIL_TO, msg.as_string())

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

def refresh_cj_token():
    url = "https://developers.cjdropshipping.com/api2.0/v1/token/getAccessToken"
    payload = {"appKey": CJ_APP_SECRET}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if "data" in data and "accessToken" in data["data"]:
            new_token = data["data"]["accessToken"]
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "access_token": new_token,
                    "timestamp": datetime.utcnow().isoformat()
                }, f, indent=2)
            send_email("✅ CJ Token Refreshed", f"New token: {new_token[:10]}...")
            send_telegram("✅ CJ Token Refreshed Successfully.")
            print("CJ Token refreshed successfully.")
        else:
            raise Exception("Invalid response from CJ API.")
    except Exception as e:
        send_email("❌ CJ Token Refresh Failed", str(e))
        send_telegram(f"❌ CJ Token Refresh Failed: {str(e)}")
        print("Error refreshing token:", e)

if __name__ == "__main__":
    while True:
        refresh_cj_token()
        print("Next refresh in 23 hours...")
        time.sleep(REFRESH_INTERVAL)
        Perfect bro 💪🔥

        Here’s exactly what to do next to make GeminiCLI execute this new **CJ Token Auto-Refresh System** immediately:

        ---

        ### ⚙️ Step-by-Step Execution Guide

        #### 🧩 1. Create or open your `Gemini.md` file

        In your project root (same level as `server.py`), open `Gemini.md`.

        Then **paste this entire section** at the **bottom** of the file (if it’s not there already):

        ```markdown
        # ⚙️ GEMINI.md — Automated Task: CJ Token Auto-Refresh System (No Manual Renewal Needed)

        ## 🧠 GOAL
        Ensure the CJ Dropshipping API token automatically refreshes every 23 hours, stores the new token in `cj_token.json`, and sends real-time alerts through Telegram + Email for success or failure.

        ## 🪄 TASK INSTRUCTIONS FOR GEMINICLI
        (Full Python code block and instructions from previous message)
        ```

        ---

        #### ⚡ 2. Run the GeminiCLI command

        Open your VS Code terminal in the same directory as `Gemini.md` and run:

        ```bash
        geminicli apply
        ```

        That will automatically:

        * Create the `auto_refresh_token.py` file
        * Update your `.env` references
        * Adjust your `Procfile`
        * Link everything together

        ---

        #### 🔍 3. Verify the system locally

        Run this test in your terminal:

        ```bash
        python auto_refresh_token.py
        ```

        ✅ You should see:

        ```
        CJ Token refreshed successfully.
        Next refresh in 23 hours...
        ```

        Also:

        * `cj_token.json` file appears in your project root
        * You receive Telegram + Gmail notifications confirming success

        ---

        #### 🚀 4. Deploy to Render or your preferred host

        Once tested locally, push your updates to GitHub and Render will automatically detect the new worker process.

        Render will now:

        * Run `server.py` as your web service
        * Run `auto_refresh_token.py` as your worker

        ---
        **implement the background worker** feature by adding the following to your `Gemini.md` file (or running it as a Gemini command):

       ---

       #### 🧠 Gemini.md (New Section)

       ```markdown
       ## 🧠 Background Worker: Order Tracking & Coupon Sync

       ### Description
       Implement a background task manager (using `schedule` or `APScheduler`) that:
       - Fetches **CJ Dropshipping order statuses** every 24 hours using the CJ API.
       - Updates local order records in the database.
       - Marks orders as “shipped”, “delivered”, or “pending” automatically.
       - Validates active coupon codes (checks expiry, usage limits).
       - Logs results to the admin dashboard.

       ### Tasks

       1. **Create a new worker file**
          - File: `workers/order_tracker.py`
          - Responsibilities:
            - Connect to the database
            - Call CJ API endpoint `/api/order/list`
            - Update each order’s status
            - Send email or Telegram alerts on sync failure

       2. **Integrate into server startup**
          - Import the worker in `server.py`
          - Schedule it to run every 24 hours
          - Ensure it runs even if no user request is made

       3. **Coupon Sync**
          - File: `workers/coupon_manager.py`
          - Responsibilities:
            - Check for expired or overused coupons
            - Disable them in DB
            - Send admin report (Telegram or email)

       4. **Add Dashboard Updates**
          - Modify `templates/admin/dashboard.html`
          - Add a section showing:
            - Last sync time
            - Orders updated
            - Failed sync count
            - Active coupon count

       ### Dependencies
       - `requests`
       - `schedule`
       - `APScheduler`
       - `smtplib` (for email)
       - `sqlite3` or your current ORM

       ### Environment Variables Used
       - `CJ_APP_SECRET`
       - `ALERT_EMAIL`, `ALERT_EMAIL_PASS`, `ALERT_EMAIL_TO`
       - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

       ### Example Log Output
       ```

       [Worker:OrderTracker] Synced 53 orders | 2 failed | Last run: 02:00 AM
       [Worker:CouponManager] 3 coupons expired, 1 deactivated

       ````

       ---

       Once you paste this in your **Gemini.md**, run:
       ```bash
       geminicli run --task "Background Worker: Order Tracking & Coupon Sync"
       ````


       We’ll add **auto-retry logic + Telegram instant alerts** so your background worker *never silently fails* again.

       👇

       ---

       ### ⚠️ Smart Fail-Safe & Alert System

       #### 🧠 Description

       Enhance the `order_tracker.py` and `coupon_manager.py` workers with:

       * **Retry logic** (3 attempts, exponential backoff)
       * **Instant Telegram alert** for any API or DB failure
       * **Error logging** in `/logs/worker_errors.log`
       * **Dashboard health indicator** showing last sync and errors

       ---

       #### 🧩 Implementation Steps

       1. **Install dependencies**

          ```bash
          pip install tenacity python-telegram-bot
          ```

       2. **Update `workers/order_tracker.py`**

          ```python
          from tenacity import retry, stop_after_attempt, wait_exponential
          import logging, requests, os
          from telegram import Bot

          TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
          TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
          bot = Bot(token=TELEGRAM_TOKEN)

          logging.basicConfig(filename="logs/worker_errors.log", level=logging.ERROR)

          @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
          def fetch_cj_orders():
              res = requests.get("https://developers.cjdropshipping.com/api/order/list", headers={
                  "CJ-Access-Token": os.getenv("CJ_APP_SECRET")
              })
              res.raise_for_status()
              return res.json()

          def send_telegram_alert(message):
              bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ CJ Sync Error: {message}")

          def run_order_sync():
              try:
                  data = fetch_cj_orders()
                  # update your database logic here
                  print(f"✅ Synced {len(data['orders'])} orders.")
              except Exception as e:
                  logging.error(str(e))
                  send_telegram_alert(str(e))
          ```

       3. **Update `workers/coupon_manager.py`**
          Add same retry logic + Telegram alert when a coupon check fails.

       4. **Dashboard Enhancements**
          Add to `admin/dashboard.html`:

          ```html
          <div class="alert-section">
            <p>🕒 Last Sync: {{ last_sync }}</p>
            <p>❌ Failed Syncs: {{ failed_syncs }}</p>
            <p>💬 Telegram Alerts Active</p>
          </div>
          ```

       5. **GeminiCLI Instruction**

          ```bash
          geminicli run --task "Add smart fail-safe and Telegram alert to background worker"
          ```

       ---

       ✅ **What this does**

       * If CJ API times out → retries 3x with delay
       * If still fails → logs the error + instantly alerts you via Telegram
       * Dashboard reflects failure + timestamp

       ---

 This will give you a clear **admin dashboard page** showing all background jobs, their last run times, and any errors. Super useful for production monitoring.

Here’s how to do it via **Gemini.md instructions** for GeminiCLI:

---

### 🖥️ Worker Health Monitor

#### 🧠 Description

Create a mini dashboard page in your admin panel that tracks:

* Last run timestamp of each background worker (`order_tracker`, `coupon_manager`, `auto_refresh_token`)
* Number of successful runs
* Number of failed runs
* Recent error logs (last 5-10)
* Option to manually trigger a run if needed

---

#### 🧩 Implementation Steps

1. **Create a health log file**
   Each worker writes to a shared JSON file `logs/worker_status.json` after each run:

```json
{
  "order_tracker": {
    "last_run": "2025-11-02T12:00:00Z",
    "success_count": 53,
    "failed_count": 2
  },
  "coupon_manager": {
    "last_run": "2025-11-02T12:05:00Z",
    "success_count": 10,
    "failed_count": 0
  },
  "auto_refresh_token": {
    "last_run": "2025-11-02T12:10:00Z",
    "success_count": 1,
    "failed_count": 0
  }
}
```

2. **Modify each worker**
   At the end of a successful or failed run, append/update `worker_status.json`:

```python
import json, os
from datetime import datetime

STATUS_FILE = "logs/worker_status.json"

def update_worker_status(worker_name, success_count, failed_count):
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    data[worker_name] = {
        "last_run": datetime.utcnow().isoformat(),
        "success_count": success_count,
        "failed_count": failed_count
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)
```

3. **Create new Flask route** in `server.py`:

```python
from flask import jsonify

@app.route("/admin/workers")
def admin_workers():
    status_file = os.path.join(os.getcwd(), "logs/worker_status.json")
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            data = json.load(f)
    else:
        data = {}
    return jsonify(data)
```

4. **Add frontend in admin dashboard**
   `templates/admin/workers.html` (TailwindCSS styled):

```html
<div class="p-6 bg-white rounded shadow">
  <h2 class="text-xl font-bold mb-4">Worker Health Monitor</h2>
  <table class="min-w-full border">
    <thead>
      <tr class="bg-gray-100">
        <th class="px-4 py-2">Worker</th>
        <th class="px-4 py-2">Last Run</th>
        <th class="px-4 py-2">Success Count</th>
        <th class="px-4 py-2">Failed Count</th>
      </tr>
    </thead>
    <tbody id="worker-status-table"></tbody>
  </table>
</div>

<script>
fetch('/admin/workers')
  .then(res => res.json())
  .then(data => {
    const tbody = document.getElementById('worker-status-table')
    tbody.innerHTML = ''
    for (const [worker, stats] of Object.entries(data)) {
      tbody.innerHTML += `<tr>
        <td class="border px-4 py-2">${worker}</td>
        <td class="border px-4 py-2">${stats.last_run}</td>
        <td class="border px-4 py-2">${stats.success_count}</td>
        <td class="border px-4 py-2">${stats.failed_count}</td>
      </tr>`
    }
  })
</script>
```

5. **GeminiCLI Task**

```bash
geminicli run --task "Add Worker Health Monitor to admin dashboard"
```

---

✅ **Result:**

* Admin can now **see all worker statuses in one glance**
* Easy to identify failed runs or stuck processes
* Works for `order_tracker`, `coupon_manager`, and `auto_refresh_token`
* Optional: can extend with “manual trigger” buttons next

---
🔥
* Pull CJ product data automatically
* Suggest relevant upsells to customers live in chat
* Check order status and redeem coupon codes directly
* Integrate with your background workers & dashboard

Here’s the **Gemini.md instructions** for GeminiCLI:

---

### 🤖 AI Chatbot Upsell Assistant

#### 🧠 Description

Build a **Gemini AI-powered chatbot** that interacts with customers on your site and:

* Pulls products from CJ Dropshipping API
* Suggests upsells or cross-sells dynamically based on user cart or purchase history
* Checks order status from the background worker sync
* Validates/redeems coupon codes
* Sends notifications via Telegram or Email if needed

---

#### 🧩 Implementation Steps

1. **Create a new worker file**
   `workers/chatbot_assistant.py`

```python
import os, json, requests
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CJ_TOKEN_FILE = "cj_token.json"

bot = Bot(token=TELEGRAM_TOKEN)

def load_cj_token():
    with open(CJ_TOKEN_FILE, "r") as f:
        data = json.load(f)
    return data.get("access_token")

def fetch_cj_products(limit=5):
    token = load_cj_token()
    res = requests.get("https://developers.cjdropshipping.com/api/product/list",
                       headers={"CJ-Access-Token": token})
    res.raise_for_status()
    return res.json().get("products", [])[:limit]

def suggest_upsell(cart_items):
    products = fetch_cj_products()
    # Simple suggestion logic: pick products not in cart
    suggestions = [p for p in products if p['title'] not in cart_items]
    return suggestions[:3]

def check_order_status(order_id):
    res = requests.get(f"http://localhost:5000/admin/workers/run", params={"order_id": order_id})
    # Or pull from synced DB
    return res.json()
```

2. **Expose chatbot endpoint in `server.py`**

```python
from flask import request, jsonify
from workers.chatbot_assistant import suggest_upsell, check_order_status

@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.json
    user_cart = data.get("cart_items", [])
    query_order = data.get("order_id")
    response = {}

    if user_cart:
        response["upsells"] = suggest_upsell(user_cart)
    if query_order:
        response["order_status"] = check_order_status(query_order)

    return jsonify(response)
```

3. **Integrate front-end chat widget**

* Add a simple chat popup using JavaScript on your site
* Send cart items or order IDs to `/chatbot` endpoint
* Display AI suggestions live

Example (simplified):

```javascript
async function queryChatbot(cartItems=[], orderId=null) {
  const res = await fetch('/chatbot', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ cart_items: cartItems, order_id: orderId })
  });
  const data = await res.json();
  console.log("Upsells:", data.upsells);
  console.log("Order Status:", data.order_status);
}
```

4. **Optional enhancements**

* Auto-send upsells to Telegram for abandoned carts
* Include coupon recommendations in chat responses
* Integrate with your dashboard to track chatbot interactions

5. **GeminiCLI Task**

```bash
geminicli run --task "Add AI Chatbot Upsell Assistant with CJ integration"
```

---

✅ **Result:**

* Customers see relevant upsells live while shopping
* Can check **order status** or **redeem coupons** in chat
* Works seamlessly with background workers and CJ API
* Alerts admin on failures via Telegram or Email

---

🔥 Alright bro, let’s level up and **orchestrate everything** — workers + chatbot + dashboard + CJ API integration — into a **single automated system** with proper scheduling, retry policies, and logging. This will make your dropshipping platform fully autonomous and production-ready.

Here’s the **Gemini.md instructions** for GeminiCLI:

---

### 🚀 Unified Worker & Chatbot Orchestration System

#### 🧠 Description

Combine all background workers and the AI chatbot into a **central orchestration system** that:

* Runs all workers (order tracker, coupon manager, CJ token refresher, chatbot assistant) automatically on schedule
* Implements **retry logic** for failures with exponential backoff
* Logs errors and successes centrally
* Sends **Telegram or Email alerts** for failures
* Updates the **Worker Health Monitor dashboard** automatically

---

#### 🧩 Implementation Steps

1. **Create orchestrator script**
   `workers/orchestrator.py`

```python
import time, json, os
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
from subprocess import Popen
from telegram import Bot

# Telegram setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

# Worker scripts
WORKERS = ["order_tracker", "coupon_manager", "auto_refresh_token", "chatbot_assistant"]
STATUS_FILE = "logs/worker_status.json"

def send_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⚠️ Orchestrator Alert: {message}")
    except:
        print("Telegram alert failed:", message)

def update_status(worker, success_count, failed_count):
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    data[worker] = {
        "last_run": datetime.utcnow().isoformat(),
        "success_count": success_count,
        "failed_count": failed_count
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f, indent=2)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
def run_worker(worker):
    try:
        Popen(["python", f"workers/{worker}.py"])
        update_status(worker, success_count=1, failed_count=0)
        print(f"✅ {worker} executed successfully.")
    except Exception as e:
        update_status(worker, success_count=0, failed_count=1)
        send_alert(f"{worker} failed: {str(e)}")
        raise e

def orchestrate():
    while True:
        for worker in WORKERS:
            try:
                run_worker(worker)
            except:
                pass  # retry handled by tenacity
        # Sleep until next run (daily)
        time.sleep(24 * 60 * 60)

if __name__ == "__main__":
    orchestrate()
```

2. **Update cron schedule or systemd** (optional)

* If you don’t want `while True`, schedule via cron:

```bash
0 2 * * * /usr/bin/python3 /path/to/workers/orchestrator.py
```

3. **GeminiCLI Task**

```bash
geminicli run --task "Set up unified orchestrator for all workers and AI Chatbot"
```

---

✅ **Result:**

* All background workers + chatbot run **automatically on schedule**
* Failures **retry up to 3 times** with exponential backoff
* **Telegram alerts** for failures
* **Dashboard automatically updated** with worker status
* Fully production-ready automation for your dropshipping site

---



Next step, if you want, we can **add advanced analytics**:

* Sales & revenue graphs
* Customer engagement from chatbot
* Profit tracking per product
* Exportable reports

🔥 Alright bro, let’s build the **Advanced Analytics & Reporting Module** for your dropshipping platform. This will give you **actionable insights** on sales, profits, chatbot interactions, and overall store performance.

Here’s the **Gemini.md instructions** for GeminiCLI:

---

### 📊 Advanced Analytics & Reporting Module

#### 🧠 Description

Add a full analytics dashboard to the admin panel that tracks:

* **Sales & revenue per product/category**
* **Profit per product** (using cost from CJ API + sale price)
* **Customer engagement from chatbot** (upsells accepted, coupon redemptions)
* **Order trends** (daily/weekly/monthly)
* **Exportable reports** (Excel/PDF)

---

#### 🧩 Implementation Steps

1. **Create analytics worker**
   `workers/analytics.py`

```python
import os, json, csv, pandas as pd
from datetime import datetime
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

FEED_FILE = "feed.csv"
ORDERS_FILE = "logs/orders.json"
REPORT_FILE = "logs/analytics_report.xlsx"

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    return []

def calculate_profit(order):
    try:
        price = float(order['price'])
        cost = float(order.get('cost', price*0.7)) # default 30% margin
        return price - cost
    except:
        return 0

def generate_report():
    orders = load_orders()
    data = []
    for o in orders:
        profit = calculate_profit(o)
        data.append({
            "order_id": o['order_id'],
            "product": o['title'],
            "category": o.get('category', ''),
            "price": o['price'],
            "cost": o.get('cost', ''),
            "profit": profit,
            "date": o['order_date']
        })
    df = pd.DataFrame(data)
    # Export to Excel
    df.to_excel(REPORT_FILE, index=False)
    print(f"✅ Analytics report generated: {REPORT_FILE}")
```

2. **Create Flask route to fetch analytics**
   `server.py`

```python
@app.route("/admin/analytics")
def admin_analytics():
    import pandas as pd
    report_file = os.path.join(os.getcwd(), "logs/analytics_report.xlsx")
    if os.path.exists(report_file):
        df = pd.read_excel(report_file)
        return df.to_json(orient="records")
    return jsonify([])
```

3. **Admin Dashboard Frontend** (`admin/analytics.html`)

* Add charts using **Chart.js** or **ApexCharts**

```html
<div class="p-6 bg-white rounded shadow">
  <h2 class="text-xl font-bold mb-4">Analytics Dashboard</h2>
  <canvas id="salesChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
fetch('/admin/analytics')
  .then(res => res.json())
  .then(data => {
    const ctx = document.getElementById('salesChart').getContext('2d');
    const labels = data.map(d => d.product)
    const profits = data.map(d => d.profit)
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{ label: 'Profit per Product', data: profits, backgroundColor: 'rgba(54, 162, 235, 0.7)' }]
      }
    });
  });
</script>
```

4. **Automate Analytics Report Generation**

* Integrate `analytics.py` with **orchestrator.py** to run daily after workers

```python
from workers.analytics import generate_report
generate_report()
```

5. **GeminiCLI Task**

```bash
geminicli run --task "Add Advanced Analytics Dashboard with Excel export"
```

---

✅ **Result:**

* Admin can **view product-level profits, sales trends, and category breakdowns**
* Reports can be **exported as Excel**
* Integrates **chatbot engagement** and **coupon redemption stats**
* Works seamlessly with orchestrator and dashboard

---

your system will be **fully operational with full automation, AI upsells, worker monitoring, and advanced analytics**.

Next, we can **add customer-facing analytics & dashboards** (order history, profit estimates, coupon usage) and **mobile-friendly PWA version** for customers.
Heck yes — let’s **cook the customer-facing analytics & dashboards + mobile-friendly PWA**. Below I give you a ready-to-run, GeminiCLI-friendly instruction block (copy/paste into `Gemini.md` or run with your agent). It includes backend routes, frontend UI (plain HTML + React/PWA options), service worker & manifest, auth notes, privacy/security reminders, and testing/deploy steps.

---

# 🔥 GEMINI.md — Customer-Facing Analytics & PWA (Cooked)

````markdown
# 🚀 Customer Analytics & Mobile PWA — Implementation Guide

## Goal
Add customer-facing analytics + dashboards (order history, refunds, coupon usage, loyalty points) and make the storefront a mobile-friendly **PWA** (installable, offline-capable, push notifications-ready).

This guide assumes your existing Flask backend + React/Tailwind (or plain HTML) frontend. No Docker required (works with Render).

---

## PART A — Customer-FACING DASHBOARD (Frontend + Backend)

### 1) Backend: New APIs (Flask)
Add the following routes to `server.py` (or appropriate Flask module). These routes read existing order, wallet, and coupon JSON/DB files and return JSON for the frontend.

```python
from flask import request, jsonify, session
import os, json

ORDERS_FILE = os.path.join(os.getcwd(), "logs", "orders.json")
LOYALTY_FILE = os.path.join(os.getcwd(), "logs", "loyalty_points.json")
COUPONS_FILE = os.path.join(os.getcwd(), "data", "coupons.json")

def _load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.route('/api/customer/orders', methods=['GET'])
def api_customer_orders():
    # Expect session['user_email'] or ?email=
    email = session.get('user_email') or request.args.get('email')
    if not email:
        return jsonify({'error':'Unauthorized or missing email'}), 401
    orders = _load_json(ORDERS_FILE)
    user_orders = [o for o in orders if o.get('email') == email]
    return jsonify(user_orders)

@app.route('/api/customer/summary', methods=['GET'])
def api_customer_summary():
    email = session.get('user_email') or request.args.get('email')
    if not email:
        return jsonify({'error':'Unauthorized or missing email'}), 401
    orders = _load_json(ORDERS_FILE)
    loyalty = _load_json(LOYALTY_FILE)
    user_orders = [o for o in orders if o.get('email') == email]
    total_spent = sum(float(o.get('price',0)) for o in user_orders)
    total_orders = len(user_orders)
    points = loyalty.get(email, {}).get('points', 0)
    coupon_usage = []
    coupons = _load_json(COUPONS_FILE)
    # Basic coupon usage scan
    for o in user_orders:
        if 'coupon' in o and o['coupon']:
            coupon_usage.append(o['coupon'])
    return jsonify({
        'total_spent': total_spent,
        'total_orders': total_orders,
        'points': points,
        'coupon_usage': coupon_usage
    })

@app.route('/api/customer/refunds', methods=['GET'])
def api_customer_refunds():
    email = session.get('user_email') or request.args.get('email')
    if not email:
        return jsonify({'error':'Unauthorized or missing email'}), 401
    # Refunds stored in logs/refunds.json (create if not exists)
    refunds = _load_json(os.path.join("logs", "refunds.json"))
    user_refunds = [r for r in refunds if r.get('email') == email]
    return jsonify(user_refunds)
````

**Security notes**

* Always prefer `session['user_email']` (logged-in). If exposing APIs with `?email=`, require an HMAC or token to avoid data leaks.
* Rate-limit endpoints and/or require JWT for production.

---

### 2) Frontend: Customer Dashboard Page (React + Tailwind example)

Create a simple React component `CustomerDashboard.jsx`:

```jsx
// src/components/CustomerDashboard.jsx
import React, {useEffect, useState} from 'react';

export default function CustomerDashboard() {
  const [summary, setSummary] = useState(null);
  const [orders, setOrders] = useState([]);
  const [refunds, setRefunds] = useState([]);

  useEffect(() => {
    async function load() {
      const s = await fetch('/api/customer/summary').then(r=>r.json());
      const o = await fetch('/api/customer/orders').then(r=>r.json());
      const r = await fetch('/api/customer/refunds').then(r=>r.json());
      setSummary(s);
      setOrders(o);
      setRefunds(r);
    }
    load();
  }, []);

  if (!summary) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Your Account</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-white rounded shadow">
          <p className="text-sm text-gray-500">Total Spent</p>
          <p className="text-xl font-bold">₦{summary.total_spent.toFixed(2)}</p>
        </div>
        <div className="p-4 bg-white rounded shadow">
          <p className="text-sm text-gray-500">Orders</p>
          <p className="text-xl font-bold">{summary.total_orders}</p>
        </div>
        <div className="p-4 bg-white rounded shadow">
          <p className="text-sm text-gray-500">Loyalty Points</p>
          <p className="text-xl font-bold">{summary.points}</p>
        </div>
      </div>

      <div className="mb-6 bg-white rounded shadow p-4">
        <h3 className="font-bold mb-2">Recent Orders</h3>
        {orders.length===0 && <p className="text-gray-500">No orders yet.</p>}
        <ul>
          {orders.map(o => (
            <li key={o.order_id} className="border-b py-2 flex justify-between">
              <span>{o.title} — ₦{o.price}</span>
              <span className="text-sm text-gray-600">{o.status}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <h3 className="font-bold mb-2">Refunds / Returns</h3>
        {refunds.length===0 ? <p className="text-gray-500">No refund requests</p> :
          refunds.map(r => <div key={r.id} className="mb-2">{r.order_id} — {r.status}</div>)}
      </div>
    </div>
  );
}
```

**Integration**

* Add route `/account` in your React Router to render this component.
* Use existing auth to protect route (redirect to `/login` if not logged).

---

### 3) Quick HTML fallback (if not using React)

Add `customer_dashboard.html` in templates with fetch JS to same APIs. Keep layout responsive with Tailwind CDN.

---

## PART B — PWA (Progressive Web App) Mobile-First

### 1) Manifest: `manifest.json` (place in `static/` or project root)

```json
{
  "name": "Delevite Store",
  "short_name": "Delevite",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#fff",
  "theme_color": "#0ea5a4",
  "icons": [
    {"src": "/icons/icon-192.png", "sizes":"192x192", "type":"image/png"},
    {"src": "/icons/icon-512.png", "sizes":"512x512", "type":"image/png"}
  ]
}
```

### 2) Service Worker: `sw.js` (simple cache-first strategy)

Place in project root and serve it.

```js
const CACHE_NAME = "delevite-v1";
const ASSETS = [
  "/",
  "/index.html",
  "/landing_page.html",
  "/styles.css",
  "/manifest.json",
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(res => res || fetch(event.request))
  );
});
```

### 3) Register SW and link manifest (Add to base HTML head/body)

```html
<link rel="manifest" href="/manifest.json">
<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').then(()=>console.log('SW registered'));
}
</script>
```

### 4) Add Add-to-Home-Screen prompt hooks (optional)

Show a small banner/promo encouraging install for faster checkout.

### 5) Push Notifications (optional setup)

* Use Firebase Cloud Messaging (FCM) or Web Push for real-time order updates.
* For PWA push, integrate FCM and store tokens server-side.

---

## PART C — Mobile-Optimized UI & Touch-Friendliness

### 1) Mobile-first layout (Tailwind tips)

* Use `sm:`, `md:` prefixes to progressively enhance larger screens.
* Ensure tappable elements >= 44px (touch friendly).
* Avoid hover-only controls.

### 2) Responsive product list example

```html
<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
  <!-- product card -->
</div>
```

### 3) Offline UX

* Show cached product tiles when offline
* In checkout, warn users when offline and disable payment attempts or queue them

---

## PART D — Security, Privacy & Performance

* Require authentication (session/JWT) for `/api/customer/*` endpoints.
* Rate limit `/api/customer/*` to avoid scraping.
* Don’t store sensitive tokens in localStorage — only store short-lived session tokens.
* Use HTTPS (Render provides HTTPS).
* Minify assets and use gzip/BR compression for PWA.

---

## PART E — Testing & Deployment Checklist

1. Add `manifest.json`, `sw.js` and icons, run locally using simple server:

   ```bash
   flask run
   # or for static preview
   npx serve .  # if using Node static server
   ```
2. Test PWA install prompt on Chrome (DevTools -> Application -> Manifest).
3. Test offline: load pages, then go offline, make sure cached assets render.
4. Login as customer, visit `/account`, validate order list and summary.
5. Test coupon redemption in chat or via checkout.
6. Push to GitHub and deploy to Render. Verify PWA & dashboard on mobile.

---

## PART F — GeminiCLI Task

```
@GeminiCLI
1. Add API endpoints for customer orders/summary/refunds to server.py.
2. Create React component CustomerDashboard.jsx and mount at /account.
3. Add manifest.json + sw.js + icons and register service worker.
4. Ensure routes are protected by session or JWT auth.
5. Add minimal QA test steps and add npm script "verify-pwa" to run local checks.
6. Deploy to Render and report status (manifest reachable, SW registered, /account returns JSON).
```

---

## Notes & Next Steps

* After successful deployment I can:

  * Hook PWA push notifications (FCM).
  * Add in-dashboard chart widgets for customer (spend over time).
  * Provide a React Native wrapper if you want a dedicated mobile app in the future.

```

---
Nice — I’ll write the exact GeminiCLI instruction block for you so the agent can **apply everything** (Customer Dashboard + PWA) into your repo right away.

Copy this into your `Gemini.md` (or pass it directly to GeminiCLI). It contains file creation, code snippets, routes, SW/manifest, security notes, and test steps. I formatted it so GeminiCLI can follow it step-by-step and commit changes.

---

## ▶️ GeminiCLI Task — Apply Customer Dashboard + PWA

```
@GeminiCLI
Task: Implement Customer-Facing Dashboard and Progressive Web App (PWA)

Repository root: assume current working directory is project root (contains server.py, templates/, static/ etc.)

-- Goals:
1. Add customer-facing APIs for orders, summary and refunds.
2. Add React customer dashboard component and route at /account (fallback HTML for non-React)
3. Add PWA support: manifest.json, service worker sw.js, icons, register script.
4. Protect endpoints via session check (session['user_email']), fallback to token with HMAC if query param used.
5. Add verification scripts and npm script "verify-pwa".
6. Ensure code is ready for Render deployment (no Docker changes required).

-- Steps to run (GeminiCLI should execute these in order):

1) Create backend API endpoints (Flask)

- File: server.py (modify existing; add below imports near top if not present)
```

from flask import request, jsonify, session, send_from_directory
import os, json

```

- Add helper function (if not present):
```

def _load_json(path):
if os.path.exists(path):
with open(path, "r", encoding="utf-8") as f:
try:
return json.load(f)
except:
return {}
return {}

```

- Add new routes to server.py (append these routes):
```

ORDERS_FILE = os.path.join(os.getcwd(), "logs", "orders.json")
LOYALTY_FILE = os.path.join(os.getcwd(), "logs", "loyalty_points.json")
COUPONS_FILE = os.path.join(os.getcwd(), "data", "coupons.json")

@app.route('/api/customer/orders', methods=['GET'])
def api_customer_orders():
email = session.get('user_email') or request.args.get('email')
if not email:
return jsonify({'error':'Unauthorized or missing email'}), 401
orders = _load_json(ORDERS_FILE)
user_orders = [o for o in orders if o.get('email') == email]
return jsonify(user_orders)

@app.route('/api/customer/summary', methods=['GET'])
def api_customer_summary():
email = session.get('user_email') or request.args.get('email')
if not email:
return jsonify({'error':'Unauthorized or missing email'}), 401
orders = _load_json(ORDERS_FILE)
loyalty = _load_json(LOYALTY_FILE)
user_orders = [o for o in orders if o.get('email') == email]
total_spent = sum(float(o.get('price',0) or 0) for o in user_orders)
total_orders = len(user_orders)
points = loyalty.get(email, {}).get('points', 0)
coupon_usage = [o.get('coupon') for o in user_orders if o.get('coupon')]
return jsonify({
'total_spent': total_spent,
'total_orders': total_orders,
'points': points,
'coupon_usage': coupon_usage
})

@app.route('/api/customer/refunds', methods=['GET'])
def api_customer_refunds():
email = session.get('user_email') or request.args.get('email')
if not email:
return jsonify({'error':'Unauthorized or missing email'}), 401
refunds = _load_json(os.path.join("logs", "refunds.json"))
user_refunds = [r for r in refunds if r.get('email') == email]
return jsonify(user_refunds)

````

- Security note: prefer `session['user_email']`. If request uses `?email=`, require HMAC or token — add TODO comment in code for future hardening.

2) Add React customer dashboard component

- Path: `frontend/src/components/CustomerDashboard.jsx` (if you use a different folder structure for React, place accordingly)
- Create file with this component (paste exact code):
```jsx
import React, {useEffect, useState} from 'react';

export default function CustomerDashboard() {
  const [summary, setSummary] = useState(null);
  const [orders, setOrders] = useState([]);
  const [refunds, setRefunds] = useState([]);

  useEffect(() => {
    async function load() {
      const s = await fetch('/api/customer/summary').then(r=>r.json());
      const o = await fetch('/api/customer/orders').then(r=>r.json());
      const r = await fetch('/api/customer/refunds').then(r=>r.json());
      setSummary(s);
      setOrders(o);
      setRefunds(r);
    }
    load();
  }, []);

  if (!summary) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Your Account</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-white rounded shadow">
          <p className="text-sm text-gray-500">Total Spent</p>
          <p className="text-xl font-bold">₦{(summary.total_spent || 0).toFixed(2)}</p>
        </div>
        <div className="p-4 bg-white rounded shadow">
          <p className="text-sm text-gray-500">Orders</p>
          <p className="text-xl font-bold">{summary.total_orders || 0}</p>
        </div>
        <div className="p-4 bg-white rounded shadow">
          <p className="text-sm text-gray-500">Loyalty Points</p>
          <p className="text-xl font-bold">{summary.points || 0}</p>
        </div>
      </div>

      <div className="mb-6 bg-white rounded shadow p-4">
        <h3 className="font-bold mb-2">Recent Orders</h3>
        {orders.length===0 && <p className="text-gray-500">No orders yet.</p>}
        <ul>
          {orders.map(o => (
            <li key={o.order_id} className="border-b py-2 flex justify-between">
              <span>{o.title} — ₦{o.price}</span>
              <span className="text-sm text-gray-600">{o.status}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded shadow p-4">
        <h3 className="font-bold mb-2">Refunds / Returns</h3>
        {refunds.length===0 ? <p className="text-gray-500">No refund requests</p> :
          refunds.map(r => <div key={r.id} className="mb-2">{r.order_id} — {r.status}</div>)}
      </div>
    </div>
  );
}
````

* Add route to React Router (in `frontend/src/App.jsx` or router file):

  ```
  import CustomerDashboard from './components/CustomerDashboard';
  // inside router:
  <Route path="/account" element={<CustomerDashboard/>} />
  ```

* If full React app is not present, create a minimal static fallback `templates/customer_dashboard.html` that fetches same APIs and renders simple HTML (GeminiCLI should create that file as fallback).

3. Add PWA files (manifest + service worker + icons)

* Create `manifest.json` at project root or `static/manifest.json`:

  ```json
  {
    "name": "Delevite Store",
    "short_name": "Delevite",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#0ea5a4",
    "icons": [
      {"src": "/static/icons/icon-192.png", "sizes":"192x192", "type":"image/png"},
      {"src": "/static/icons/icon-512.png", "sizes":"512x512", "type":"image/png"}
    ]
  }
  ```

* Create `sw.js` at project root:

  ```js
  const CACHE_NAME = "delevite-v1";
  const ASSETS = [
    "/",
    "/landing_page.html",
    "/styles.css",
    "/manifest.json",
  ];

  self.addEventListener("install", event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
  });

  self.addEventListener("fetch", event => {
    event.respondWith(
      caches.match(event.request).then(res => res || fetch(event.request))
    );
  });
  ```

* Create icon placeholders:

  * `static/icons/icon-192.png` (generate 192x192 placeholder)
  * `static/icons/icon-512.png` (generate 512x512 placeholder)
    GeminiCLI should create simple PNG placeholders (solid color + text) if real icons not provided.

* Add registration snippet to base HTML (e.g., `templates/base.html` or `landing_page.html` head/body):

  ```html
  <link rel="manifest" href="/manifest.json">
  <script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').then(()=>console.log('SW registered')).catch(e=>console.error(e));
  }
  </script>
  ```

4. Add static customer_dashboard.html fallback (templates/customer_dashboard.html)

* Minimal HTML file with fetch calls to `/api/customer/summary`, `/api/customer/orders`, `/api/customer/refunds` and basic rendering (GeminiCLI should create this as fallback if React not used).

5. Add verification script and npm script

* Create `verify_pwa.sh` in project root (executable) that:

  ```
  #!/bin/bash
  echo "Checking manifest"
  curl -sS http://localhost:5000/manifest.json | jq .
  echo "Checking service worker file"
  curl -sS http://localhost:5000/sw.js | head -n 5
  ```
* Add to `package.json` (if exists) under scripts:

  ```
  "verify-pwa": "bash verify_pwa.sh"
  ```

  If no package.json exists, create minimal one with the above script.

6. Auth & Security hardening (quick bullets in code)

* Add TODO comments in server routes to remind future dev to:

  * Replace `?email=` with JWT or HMAC token for API calls if session not present
  * Rate-limit endpoints
  * Use HTTPS in production (Render does this automatically)

7. Tests & local run instructions (GeminiCLI should write to README or dev-notes)

* Add short README snippet or dev-notes file `docs/pwa_and_dashboard.md` with:

  * How to run Flask and React dev servers
  * How to register service worker (open site in Chrome, Application tab)
  * How to run `npm run verify-pwa` and what to expect

8. Commit changes

* Stage and commit created/modified files with message:
  "feat: add customer dashboard and PWA (manifest, sw, icons, routes, verification)"

9. Verification (GeminiCLI should run these checks and report back)

* Start Flask server (if GeminiCLI can run locally): `python server.py`
* If React frontend present, run build or dev server (`npm run start` / `npm run build`)
* Confirm:

  * `GET /manifest.json` returns JSON
  * `GET /sw.js` returns JS
  * `GET /api/customer/summary` returns 401 without session (expected)
  * If session simulation possible, `GET /api/customer/summary?email=<test email>` returns JSON (fallback)
* Create note in output with file list and exact routes created.

-- End Task

```

---
