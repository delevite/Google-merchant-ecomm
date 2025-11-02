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
