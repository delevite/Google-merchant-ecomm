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


