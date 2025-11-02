
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
