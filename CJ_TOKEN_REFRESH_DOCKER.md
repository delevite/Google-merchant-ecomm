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
<!-- Import failed: GeminiCLI: - ENOENT: no such file or directory, access 'C:\Users\Delev\Google merchant ecomm\GeminiCLI:' -->
1. Create src/utils/notifier.js using the code above.
2. Patch src/services/tokenRefresher.js to import and use sendAlert().
3. Add new environment variables for EMAIL/TELEGRAM notifications.
4. Test locally with expired CJ_REFRESH_TOKEN.
5. Confirm alerts received successfully.
```
