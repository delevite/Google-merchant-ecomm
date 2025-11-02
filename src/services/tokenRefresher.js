import axios from "axios";
import fs from "fs";
import dotenv from "dotenv";
import { sendAlert } from "../utils/notifier.js";
dotenv.config();

const CJ_REFRESH_URL =
  "https://developers.cjdropshipping.com/api2.0/v1/token/refresh";
const TOKEN_FILE = "./tmp/cj_token_cache.json";

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

      // Update environment for runtime
      process.env.CJ_ACCESS_TOKEN = accessToken;
      process.env.CJ_REFRESH_TOKEN = refreshToken;

      // Cache tokens for backup
      fs.mkdirSync("./tmp", { recursive: true });
      fs.writeFileSync(
        TOKEN_FILE,
        JSON.stringify(
          { accessToken, refreshToken, updated: new Date() },
          null,
          2,
        ),
      );

      console.log("✅ CJ Access Token refreshed successfully!");
      return accessToken;
    } else {
      console.error("❌ CJ Refresh Failed:", response.data);
      await sendAlert(
        `Token refresh failed: ${response.data.msg || "Unknown error"}`,
      );
    }
  } catch (err) {
    console.error("⚠️ Error refreshing CJ token:", err.message);
    await sendAlert(`Error during CJ refresh: ${err.message}`);
  }
}
