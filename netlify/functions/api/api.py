from flask import (
    Flask,
    send_from_directory,
    make_response,
    jsonify,
    request,
    redirect,
    session,
    render_template_string,
)
from flask_cors import CORS
import io
import logging
from collections import defaultdict
from werkzeug.security import generate_password_hash
import os
import csv
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
import uuid
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import base64
from reportlab.lib.pagesizes import letter
import traceback

# --- Phase 3: Merchant API Integration ---
try:
    from src.merchant_api import get_merchant_client, get_merchant_scheduler
    MERCHANT_API_ENABLED = os.getenv("MERCHANT_API_ENABLED", "True").lower() == "true"
except ImportError:
    MERCHANT_API_ENABLED = False
    logger.warning("Phase 3: Merchant API module not available")

# Initialize Merchant API client
_merchant_client = None
if MERCHANT_API_ENABLED:
    try:
        _merchant_client = get_merchant_client()
        if _merchant_client:
            logger.info("✓ Phase 3: Merchant API client initialized")
    except Exception as e:
        logger.warning(f"Phase 3: Could not initialize Merchant API: {e}")

# --- Phase 4: Native Checkout & AI Agent Support ---
try:
    from src.mcp_server import mcp_bp
    from src.a2a_router import A2ARouter
    from src.checkout_service import CheckoutService
    from src.conversion_tracker import ConversionTracker
    PHASE4_ENABLED = True
    logger.info("✓ Phase 4: All modules imported successfully")
except ImportError as e:
    PHASE4_ENABLED = False
    logger.warning(f"Phase 4: Could not import modules: {e}")

# Initialize Phase 4 components
_a2a_router = None
_checkout_service = None
_conversion_tracker = None


app = Flask(__name__, static_folder=os.path.join(os.getcwd(), "static"))
CORS(app)
app.secret_key = os.environ.get(
    "ADMIN_SECRET_KEY", "changeme"
)  # Set a strong secret in production

# Load environment variables from a .env file
load_dotenv()

# --- Phase 4: Initialize Components ---
if PHASE4_ENABLED:
    try:
        _a2a_router = A2ARouter(merchant_client=_merchant_client)
        _checkout_service = CheckoutService(_a2a_router, merchant_client=_merchant_client)
        _conversion_tracker = ConversionTracker()
        app.register_blueprint(mcp_bp)
        logger.info("✓ Phase 4: Components initialized and MCP blueprint registered")
    except Exception as e:
        logger.warning(f"Phase 4: Could not initialize components: {e}")

# --- Gemini API Setup ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
if not os.getenv("GEMINI_API_KEY"):
    print("Warning: GEMINI_API_KEY environment variable not set.")


# Serve static legal/info pages so nav links work locally
@app.route("/about.html")
def about():
    return send_from_directory(os.getcwd(), "about.html")


@app.route("/terms.html")
def terms():
    return send_from_directory(os.getcwd(), "terms.html")


@app.route("/privacy.html")
def privacy():
    return send_from_directory(os.getcwd(), "privacy.html")


@app.route("/contact.html")
def contact():
    return send_from_directory(os.getcwd(), "contact.html")


# Serve the generated blog index from /site/blog.html for /blog.html
@app.route("/blog.html")
def blog_index():
    return send_from_directory(os.path.join(os.getcwd(), "site"), "blog.html")


@app.route("/2025-trending-products.html")
def trending_products():
    return send_from_directory(
        os.path.join(os.getcwd(), "site"), "2025-trending-products.html"
    )


@app.route("/tag-products.html")
def tag_products():
    return send_from_directory(os.path.join(os.getcwd(), "site"), "tag-products.html")


# Generic route for other tag pages, e.g., /tag-trending.html or /tag-2025.html
# This will serve files like site/tag-trending.html or site/tag-2025.html
@app.route("/tag-<string:tag_slug>.html")
def serve_tag_page_generic(tag_slug):
    return send_from_directory(
        os.path.join(os.getcwd(), "site"), f"tag-{tag_slug}.html"
    )


# --- Phase 1: Admin Authentication with Security ---
ADMIN_CREDS_FILE = os.path.join(os.getcwd(), "admin_creds.json")

def _ensure_admin_creds():
    """Initialize admin credentials file with hashed password if not exists."""
    if not os.path.exists(ADMIN_CREDS_FILE):
        # Use environment variables or defaults, BUT store hashed password
        default_username = os.environ.get("ADMIN_USERNAME", "admin")
        default_password = os.environ.get("ADMIN_PASSWORD", "password")
        hashed_pw = generate_password_hash(default_password)
        admin_data = {
            "username": default_username,
            "password_hash": hashed_pw,
            "created_at": datetime.now().isoformat()
        }
        _save_json(ADMIN_CREDS_FILE, admin_data)


def _get_admin_creds():
    """Load admin credentials from file."""
    try:
        if os.path.exists(ADMIN_CREDS_FILE):
            with open(ADMIN_CREDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except json.JSONDecodeError:
        pass
    # Fallback to environment variables (for backwards compatibility)
    return {
        "username": os.environ.get("ADMIN_USERNAME", "admin"),
        "password_hash": generate_password_hash(os.environ.get("ADMIN_PASSWORD", "password"))
    }


_ensure_admin_creds()
ADMIN_CREDS = _get_admin_creds()
ADMIN_USERNAME = ADMIN_CREDS.get("username", "admin")
ADMIN_PASSWORD_HASH = ADMIN_CREDS.get("password_hash", generate_password_hash("password"))

# Serve static files from the 'site' directory if requested with /site/ prefix


# This will handle requests like /site/tag-trending.html
@app.route("/site/<path:filename>")
def serve_from_site_prefixed(filename):
    # send_from_directory helps prevent directory traversal attacks.
    return send_from_directory(os.path.join(os.getcwd(), "site"), filename)


UPLOAD_HISTORY_FILE = os.path.join(os.getcwd(), "upload_history.json")

# --- Phase 1: Data Persistence Files --- 
DATA_DIR = os.path.join(os.getcwd(), "data")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
LOYALTY_FILE = os.path.join(DATA_DIR, "loyalty.json")


def _ensure_data_files():
    """Initialize data directory and required files if they don't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    if not os.path.exists(LOYALTY_FILE):
        with open(LOYALTY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load_json(filepath):
    """Safely load JSON from file; return empty list or dict if file doesn't exist."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    # Return default based on expected structure
    if "loyalty" in filepath.lower():
        return {}
    return []


def _save_json(filepath, data):
    """Safely save data to JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# Initialize data files on startup
_ensure_data_files()


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.route("/")
def index():
    # Serve the landing page HTML
    return send_from_directory(os.getcwd(), "landing_page.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/feed.csv")
def feed():
    # Serve the CSV product feed
    return send_from_directory(os.getcwd(), "feed.csv")


def fetch_cj_products():
    products = []

    def clean_value(value):
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            try:
                data = json.loads(value)
                if isinstance(data, list):
                    cleaned_data = [
                        str(item)
                        for item in data
                        if isinstance(item, str)
                        and item.strip()
                        and not item.strip().isdigit()
                        and item.strip().lower() != "cosplay"
                    ]
                    return ", ".join(cleaned_data)
            except json.JSONDecodeError:
                return value
        return value

    with open(
        os.path.join(os.getcwd(), "feed.csv"), newline="", encoding="utf-8"
    ) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row["description"] = clean_value(row.get("description", ""))
            row["brand"] = clean_value(row.get("brand", ""))
            row["category"] = clean_value(row.get("category", ""))
            products.append(row)
    return products


@app.route("/products")
def get_products():
    search = request.args.get("search", "").strip().lower()
    category = request.args.get("category", "").strip()
    min_price = float(request.args.get("min_price", 0) or 0)
    max_price = float(request.args.get("max_price", float("inf")) or float("inf"))
    all_products = fetch_cj_products()
    filtered = []
    for p in all_products:
        try:
            price = float(p["price"])
        except Exception:
            price = 0
        # Search filter
        matches_search = (
            not search
            or search in p.get("title", "").lower()
            or search in p.get("description", "").lower()
            or search in p.get("brand", "").lower()
            or search in p.get("category", "").lower()
        )
        if price >= min_price and price <= max_price and matches_search:
            if not category or category.lower() in p["category"].lower():
                filtered.append(p)
    return jsonify(filtered)


@app.route("/product")
def get_product():
    title = request.args.get("title")
    if not title:
        return "Product title is required", 400

    all_products = fetch_cj_products()
    product = next((p for p in all_products if p["title"] == title), None)

    if product:
        return jsonify(product)
    else:
        return "Product not found", 404


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Use check_password_hash for secure comparison
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect("/admin")
        return render_template_string(
            '<p class="text-red-600">Invalid credentials</p>' + LOGIN_FORM
        )
    return render_template_string(LOGIN_FORM)


LOGIN_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Admin Login</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet"/>
</head>
<body class="bg-gray-50 font-sans min-h-screen flex flex-col">
  <main class="flex-1 flex flex-col items-center justify-center">
    <form method="POST" class="bg-white p-8 rounded shadow-md w-full max-w-md mt-8">
      <h2 class="text-xl font-bold mb-4">Admin Login</h2>
      <input type="text" name="username" placeholder="Username" class="mb-4 p-2 border rounded w-full" required />
      <input type="password" name="password" placeholder="Password" class="mb-6 p-2 border rounded w-full" required />
      <button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 w-full">Login</button>
    </form>
  </main>
</body>
</html>
"""


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin/login")


@app.route("/admin")
def admin_page():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    return send_from_directory(os.getcwd(), "admin.html")


def log_upload(filename, username):
    entry = {
        "filename": filename,
        "username": username,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if os.path.exists(UPLOAD_HISTORY_FILE):
        with open(UPLOAD_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    history.append(entry)
    with open(UPLOAD_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


@app.route("/admin/upload", methods=["POST"])
def upload_feed():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if "csvFile" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["csvFile"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are allowed"}), 400
    filename = secure_filename("feed.csv")
    file.save(os.path.join(os.getcwd(), filename))
    log_upload(filename, session.get("admin_user", "admin"))
    return jsonify({"message": "Feed uploaded successfully!"}), 200


@app.route("/admin/history")
def upload_history():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    if os.path.exists(UPLOAD_HISTORY_FILE):
        with open(UPLOAD_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    return jsonify(history)


@app.route("/admin/change-credentials", methods=["POST"])
def change_credentials():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_user = data.get("username")
    new_pass = data.get("password")
    if not new_user or not new_pass:
        return jsonify({"error": "Username and password required"}), 400
    # Save hashed password (security improvement)
    hashed_pw = generate_password_hash(new_pass)
    admin_data = {
        "username": new_user,
        "password_hash": hashed_pw,
        "updated_at": datetime.now().isoformat()
    }
    _save_json(ADMIN_CREDS_FILE, admin_data)
    global ADMIN_USERNAME, ADMIN_PASSWORD_HASH
    ADMIN_USERNAME = new_user
    ADMIN_PASSWORD_HASH = hashed_pw
    return jsonify({"message": "Credentials updated. Please log in again."})


@app.before_request
def load_admin_creds():
    """Load admin credentials from file (called before each request)."""
    global ADMIN_USERNAME, ADMIN_PASSWORD_HASH
    if os.path.exists(ADMIN_CREDS_FILE):
        try:
            with open(ADMIN_CREDS_FILE, "r", encoding="utf-8") as f:
                creds = json.load(f)
                ADMIN_USERNAME = creds.get("username", ADMIN_USERNAME)
                ADMIN_PASSWORD_HASH = creds.get("password_hash", ADMIN_PASSWORD_HASH)
        except (json.JSONDecodeError, IOError):
            pass


@app.route("/admin/products", methods=["GET", "POST", "DELETE"])
def manage_products():
    if not session.get("admin_logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    if request.method == "GET":
        return jsonify(fetch_cj_products())
    elif request.method == "POST":
        # Add or update a product
        data = request.json
        products = fetch_cj_products()
        # If title exists, update; else, add
        found = False
        for p in products:
            if p["title"] == data.get("title"):
                p.update(data)
                found = True
                break
        if not found:
            products.append(data)
        # Write back to CSV
        with open(
            os.path.join(os.getcwd(), "feed.csv"), "w", encoding="utf-8", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=products[0].keys())
            writer.writeheader()
            writer.writerows(products)
        return jsonify({"message": "Product saved."})
    elif request.method == "DELETE":
        # Delete a product by title
        title = request.args.get("title")
        products = fetch_cj_products()
        products = [p for p in products if p["title"] != title]
        if products:
            with open(
                os.path.join(os.getcwd(), "feed.csv"), "w", encoding="utf-8", newline=""
            ) as f:
                writer = csv.DictWriter(f, fieldnames=products[0].keys())
                writer.writeheader()
                writer.writerows(products)
        return jsonify({"message": "Product deleted."})


# --- Implementation of Task #4: AI Product Tag Generator ---
from functools import wraps
from time import time

request_counts = {}
RATE_LIMIT = 5  # 5 requests per minute
TIME_WINDOW = 60  # 60 seconds (1 minute)


def generate_tags():
    """
    Accepts a product title and description and returns AI-generated SEO tags.
    Expects a JSON payload with 'title' and 'description' keys.
    """
    if not os.getenv("GEMINI_API_KEY"):
        return jsonify(
            {"error": "Gemini API key is not configured on the server."}
        ), 500

    from functools import wraps

    data = request.get_json()
    if not data or "title" not in data or "description" not in data:
        return jsonify(
            {"error": "Missing 'title' or 'description' in request body"}
        ), 400

    product_title = data["title"]
    product_description = data["description"]

    try:
        # Initialize the Gemini Pro model
        model = genai.GenerativeModel("gemini-pro")

        # Example prompt as per your GEMINI.md
        prompt = f"Generate 5-7 SEO-friendly product tags for a product with the title '{product_title}' and description '{product_description}'. Return the tags as a single comma-separated string."

        response = model.generate_content(prompt)

        # The response from Gemini is in response.text
        tags_string = response.text.strip()
        tags_list = [tag.strip() for tag in tags_string.split(",") if tag.strip()]

        return jsonify({"product_title": product_title, "generated_tags": tags_list})

    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        return jsonify(
            {"error": f"An error occurred with the AI service: {str(e)}"}
        ), 503


def rate_limit(limit=RATE_LIMIT, per=TIME_WINDOW):
    """
    Decorator to rate-limit API calls based on the originating IP address.
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip_address = request.remote_addr
            now = time()

            # Clean up old requests
            request_counts[ip_address] = [
                t for t in request_counts.get(ip_address, []) if t > now - per
            ]

            # Check if limit is exceeded
            if len(request_counts.get(ip_address, [])) >= limit:
                return jsonify({"error": "Rate limit exceeded"}), 429

            # Record the current request
            request_counts.setdefault(ip_address, []).append(now)

            return f(*args, **kwargs)

        return wrapped

    return decorator


# --- Vendor Management (Task #5) ---


VENDOR_REGISTER_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Vendor Registration</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet"/>
</head>
<body class="bg-gray-50 font-sans min-h-screen flex flex-col">
  <main class="flex-1 flex flex-col items-center justify-center">
    <form method="POST" class="bg-white p-8 rounded shadow-md w-full max-w-md mt-8">
      <h2 class="text-xl font-bold mb-4">Vendor Registration</h2>
      <input type="text" name="username" placeholder="Username" class="mb-4 p-2 border rounded w-full" required />
      <input type="password" name="password" placeholder="Password" class="mb-6 p-2 border rounded w-full" required />
      <button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 w-full">Register</button>
    </form>
  </main>
</body>
</html>
"""


@app.route("/vendor/register", methods=["GET", "POST"])
def vendor_register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Generate a unique vendor ID
        vendor_id = str(uuid.uuid4())

        vendor = {
            "id": vendor_id,
            "username": username,
            "password_hash": hashed_password,  # Store the hashed password
        }

        save_vendor(vendor)
        return redirect("/vendor/login")

    return render_template_string(VENDOR_REGISTER_FORM)


VENDORS_FILE = os.path.join(os.getcwd(), "data", "vendors.json")


def load_vendors():
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not os.path.exists(VENDORS_FILE):
        with open(VENDORS_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(VENDORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Handle the case where the file is empty or contains invalid JSON
        return []

    with open(VENDORS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_vendor(username):
    vendors = load_vendors()
    for vendor in vendors:
        if vendor["username"] == username:
            return vendor
    return None


def save_vendor(vendor):
    vendors = load_vendors()
    vendors.append(vendor)
    with open(VENDORS_FILE, "w", encoding="utf-8") as f:
        json.dump(vendors, f, indent=4)


VENDOR_LOGIN_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Vendor Login</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet"/>
</head>
<body class="bg-gray-50 font-sans min-h-screen flex flex-col">
  <main class="flex-1 flex flex-col items-center justify-center">
    <form method="POST" class="bg-white p-8 rounded shadow-md w-full max-w-md mt-8">
      <h2 class="text-xl font-bold mb-4">Vendor Login</h2>
      <input type="text" name="username" placeholder="Username" class="mb-4 p-2 border rounded w-full" required />
      <input type="password" name="password" placeholder="Password" class="mb-6 p-2 border rounded w-full" required />
      <button type="submit" class="bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 w-full">Login</button>
    </form>
  </main>
</body>
</html>
"""


@app.route("/vendor/login", methods=["GET", "POST"])
def vendor_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        vendor = get_vendor(username)
        if vendor and check_password_hash(vendor["password_hash"], password):
            session["vendor_logged_in"] = True
            session["vendor_id"] = vendor["id"]
            return redirect("/vendor/dashboard")
        return render_template_string(
            '<p class="text-red-600">Invalid credentials</p>' + VENDOR_LOGIN_FORM
        )
    return render_template_string(VENDOR_LOGIN_FORM)


@app.route("/vendor/logout")
def vendor_logout():
    session.pop("vendor_logged_in", None)
    session.pop("vendor_id", None)
    return redirect("/vendor/login")


@app.route("/vendor/dashboard")
def vendor_dashboard():
    if not session.get("vendor_logged_in"):
        return redirect("/vendor/login")
    vendor_id = session.get("vendor_id", "Unknown")
    # A simple dashboard page for the vendor
    DASHBOARD_HTML = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>Vendor Dashboard</title>
      <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet"/>
    </head>
    <body class="bg-gray-100 p-8">
      <h1 class="text-2xl font-bold">Welcome to your Dashboard, {vendor_id}!</h1>
      <p class="mt-4">Here you can manage your products and view your orders.</p>
      <a href="/vendor/products" class="text-blue-600 hover:underline mt-8 inline-block">Manage Products</a>
      <a href="/vendor/logout" class="text-blue-600 hover:underline mt-8 inline-block">Logout</a>
    </body>
    </html>
    """
    return render_template_string(DASHBOARD_HTML)


# --- PDF Invoice Generation (Task #6) ---
INVOICES_DIR = os.path.join(os.getcwd(), "invoices")


def generate_invoice_pdf(order_details):
    """Generates a PDF invoice for a given order."""
    if not os.path.exists(INVOICES_DIR):
        os.makedirs(INVOICES_DIR)

    order_id = order_details["id"]
    file_path = os.path.join(INVOICES_DIR, f"invoice_{order_id}.pdf")

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(1 * inch, height - 1 * inch, "INVOICE")
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.5 * inch, f"Order ID: {order_id}")
    c.drawString(
        1 * inch,
        height - 1.7 * inch,
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )

    c.line(1 * inch, height - 3.6 * inch, width - 1 * inch, height - 3.6 * inch)
    y_pos = height - 3.9 * inch
    for item in order_details.get("items", []):
        c.drawString(1 * inch, y_pos, item.get("name", ""))
        c.drawString(
            6.75 * inch, y_pos, f"${item.get('price', 0) * item.get('quantity', 1):.2f}"
        )
        y_pos -= 0.3 * inch

    c.line(1 * inch, y_pos + 0.1 * inch, width - 1 * inch, y_pos + 0.1 * inch)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(5 * inch, y_pos - 0.3 * inch, "Total:")
    c.drawString(
        6.5 * inch, y_pos - 0.3 * inch, f"${order_details.get('total', 0):.2f}"
    )

    c.save()


@app.route("/order/create", methods=["POST"])
def create_order():
    """A mock endpoint to simulate creating an order and generating an invoice."""
    data = request.get_json() or {}
    items = data.get(
        "items", [{"name": "Sample Product", "price": 19.99, "quantity": 2}]
    )
    total_price = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    order_id = str(uuid.uuid4())[:8]
    order_details = {"id": order_id, "items": items, "total": total_price}
    generate_invoice_pdf(order_details)
    invoice_url = f"/invoices/invoice_{order_id}.pdf"
    return jsonify(
        {"message": "Order created", "order_id": order_id, "invoice_url": invoice_url}
    )


@app.route("/invoices/<path:filename>")
def download_invoice(filename):
    """Serves a generated invoice file for download."""
    return send_from_directory(INVOICES_DIR, filename, as_attachment=True)


def calculate_profit():
    """Calculates profit from orders.  Since we don't have real order data,
    we'll simulate it for this example."""
    products = fetch_cj_products()
    # products is a list of dictionaries

    daily_profit = defaultdict(float)
    weekly_profit = defaultdict(float)
    monthly_profit = defaultdict(float)

    for product in products:
        try:
            price = float(product["price"])
        except ValueError:
            continue

        # Assume a cost of 60% of the price
        cost = price * 0.6
        profit = price - cost


def generate_inventory_graph():
    """Generates a dummy inventory graph using matplotlib."""
    # Simulate inventory data
    products = ["Product A", "Product B", "Product C", "Product D"]
    stock_levels = [50, 80, 30, 60]

    # Create the bar chart
    plt.figure(figsize=(8, 6))
    plt.bar(products, stock_levels, color="skyblue")
    plt.xlabel("Products")
    plt.ylabel("Stock Levels")
    plt.title("Inventory Status")
    plt.ylim(0, max(stock_levels) + 20)  # Set y-axis limit

    # Save the graph to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    plt.close()

    return img


@app.route("/admin/inventory-dashboard")
def inventory_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    img = generate_inventory_graph()
    img_base64 = base64.b64encode(img.read()).decode()

    dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Inventory Dashboard</title></head>
        <body>
            <h1>Inventory Dashboard</h1>
            <img src="data:image/png;base64,{img_base64}" alt="Inventory Graph">
        </body>
        </html>
    """
    return dashboard_html


@app.route("/admin/inventory-insights")
def inventory_insights():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    from generate_inventory_insights import generate_inventory_insights

    generate_inventory_insights()

    with open("inventory_insights.txt", "r", encoding="utf-8") as f:
        content = f.read()

    return f"<pre>{content}</pre>"


@app.route("/admin/profit-report")
def profit_report():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    profit_data = calculate_profit()

    report = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Profit Report</title></head>
        <body>
            <h1>Profit Report</h1>
            <p>Total Profit: ${profit_data:.2f}</p>
        </body>
        </html>
    """

    return report


def calculate_profit():
    """Calculates profit from orders.  Since we don't have real order data,
    we'll simulate it for this example."""
    products = fetch_cj_products()
    # products is a list of dictionaries

    daily_profit = defaultdict(float)
    weekly_profit = defaultdict(float)
    monthly_profit = defaultdict(float)

    for product in products:
        try:
            price = float(product["price"])
        except ValueError:
            continue

        # Assume a cost of 60% of the price
        cost = price * 0.6
        profit = price - cost


VENDOR_PRODUCTS_FILE = os.path.join(os.getcwd(), "data", "vendor_products.json")


def load_vendor_products(vendor_id):
    """Loads vendor products from the JSON file."""
    if not os.path.exists(VENDOR_PRODUCTS_FILE):
        return []

    try:
        with open(VENDOR_PRODUCTS_FILE, "r", encoding="utf-8") as f:
            all_products = json.load(f)
            # Filter products by vendor_id
            vendor_products = [
                p for p in all_products if p.get("vendor_id") == vendor_id
            ]
            return vendor_products
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_vendor_products(vendor_id, products):
    """Saves vendor products to the JSON file, preserving products of other vendors."""
    all_products = []
    # Load all products if the file exists
    if os.path.exists(VENDOR_PRODUCTS_FILE):
        try:
            with open(VENDOR_PRODUCTS_FILE, "r", encoding="utf-8") as f:
                all_products = json.load(f)
        except json.JSONDecodeError:
            all_products = []

    # Remove existing products for this vendor
    all_products = [p for p in all_products if p.get("vendor_id") != vendor_id]

    # Add the new products for this vendor
    for product in products:
        product["vendor_id"] = vendor_id  # Ensure vendor_id is set
        all_products.append(product)

    # Write all products back to the file
    with open(VENDOR_PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4)


@app.route("/vendor/products", methods=["GET", "POST"])
def manage_vendor_products():
    """Manages vendor products - GET returns list, POST adds a new product."""
    if not session.get("vendor_logged_in"):
        return redirect("/vendor/login")

    vendor_id = session.get("vendor_id")
    if not vendor_id:
        return "Vendor ID not found in session", 400

    if request.method == "GET":
        products = load_vendor_products(vendor_id)
        return jsonify(products)

    elif request.method == "POST":
        product_data = request.get_json()
        if not product_data:
            return "No product data received", 400

        # Load existing products for this vendor
        products = load_vendor_products(vendor_id)

        # Add the new product
        products.append(product_data)

        # Save the updated list of products
        save_vendor_products(vendor_id, products)

        return jsonify({"message": "Product added successfully"}), 201


@app.route("/vendor/products/<int:product_id>", methods=["PUT", "DELETE"])
def manage_single_vendor_product(product_id):
    """Edits or deletes a single product for a vendor."""
    if not session.get("vendor_logged_in"):
        return redirect("/vendor/login")

    vendor_id = session.get("vendor_id")
    if not vendor_id:
        return "Vendor ID not found in session", 400

    products = load_vendor_products(vendor_id)
    product_index = None

    # Find the product by its index
    for i, product in enumerate(products):
        if product.get("id") == product_id:
            product_index = i
            break

    if product_index is None:
        return "Product not found", 404

    if request.method == "PUT":
        # Update the product
        product_data = request.get_json()
        if not product_data:
            return "No product data received", 400

        # Update the product with the new data
        products[product_index].update(product_data)
        save_vendor_products(vendor_id, products)
        return jsonify({"message": "Product updated successfully"})

    elif request.method == "DELETE":
        # Delete the product
        del products[product_index]
        save_vendor_products(vendor_id, products)
        return jsonify({"message": "Product deleted successfully"})


@app.route("/api/refund", methods=["POST"])
def refund_handler():
    user_message = request.json.get("message", "")
    user_email = request.json.get("email", "")
    import subprocess, json

    try:
        result = subprocess.run(
            ["node", "src/ai/intentRouter.js", user_message, user_email],
            capture_output=True,
            text=True,
        )
        response = result.stdout.strip()
    except Exception as e:
        response = json.dumps({"error": str(e)})
    return jsonify({"reply": response})


@app.route("/api/order", methods=["POST"])
def order_and_coupon_handler():
    user_message = request.json.get("message", "")
    import subprocess, json

    try:
        result = subprocess.run(
            ["node", "src/ai/orderAndCouponAssistant.js", user_message],
            capture_output=True,
            text=True,
        )
        response = result.stdout.strip()
    except Exception as e:
        response = json.dumps({"error": str(e)})
    return jsonify({"reply": response})


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    import subprocess, json

    try:
        result = subprocess.run(
            ["node", "src/services/chatbotAssistant.js", user_message],
            capture_output=True,
            text=True,
        )
        response = result.stdout.strip()
    except Exception as e:
        response = json.dumps({"error": str(e)})
    return jsonify({"reply": response})

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


# ============================================================================
# --- PHASE 3: MERCHANT API INTEGRATION ENDPOINTS ---
# ============================================================================

@app.route('/api/sync-merchant-api', methods=['POST'])
def sync_merchant_api():
    """
    Trigger real-time synchronization with Merchant Center.
    
    POST /api/sync-merchant-api
    Optional JSON body: { "feed_path": "path/to/feed.tsv" }
    
    Returns: {
        "success": bool,
        "products_synced": int,
        "products_failed": int,
        "duration_seconds": float,
        "timestamp": ISO timestamp
    }
    """
    if not MERCHANT_API_ENABLED or _merchant_client is None:
        return jsonify({
            "error": "Merchant API not enabled or not initialized",
            "hint": "Check GCP_PROJECT_ID and google-cloud-merchant installation"
        }), 503
    
    try:
        data = request.get_json() or {}
        feed_path = data.get("feed_path", "gmc_product_feed.tsv")
        
        # Trigger sync
        success, stats = _merchant_client.sync_products_from_feed(feed_path)
        
        response = {
            "success": success,
            "products_synced": stats.get("products_synced", 0),
            "products_failed": stats.get("products_failed", 0),
            "duration_seconds": stats.get("duration_seconds", 0),
            "timestamp": stats.get("timestamp", datetime.now().isoformat()),
            "merchant_id": _merchant_client.merchant_id
        }
        
        if not success:
            response["error"] = stats.get("error", "Unknown error")
            return jsonify(response), 500
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/merchant-insights', methods=['GET'])
def merchant_insights():
    """
    Retrieve performance insights from Merchant Center.
    
    GET /api/merchant-insights?days=30
    
    Returns: {
        "period_days": int,
        "metrics": {
            "impressions": int,
            "clicks": int,
            "orders": int,
            "revenue": float,
            "conversion_rate": float
        },
        "timestamp": ISO timestamp
    }
    """
    if not MERCHANT_API_ENABLED or _merchant_client is None:
        return jsonify({
            "error": "Merchant API not enabled"
        }), 503
    
    try:
        days = int(request.args.get("days", 30))
        insights = _merchant_client.get_insights(days=days)
        return jsonify(insights), 200
    
    except ValueError:
        return jsonify({"error": "Invalid days parameter"}), 400
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/merchant-sync-status', methods=['GET'])
def merchant_sync_status():
    """
    Get status of Merchant API synchronization.
    
    GET /api/merchant-sync-status
    
    Returns: {
        "products_synced": int,
        "products_failed": int,
        "last_sync_time": ISO timestamp or null,
        "last_error": string or null,
        "client_initialized": bool
    }
    """
    if not MERCHANT_API_ENABLED or _merchant_client is None:
        return jsonify({"error": "Merchant API not enabled"}), 503
    
    try:
        stats = _merchant_client.get_sync_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/merchant-inventory', methods=['GET'])
def merchant_inventory():
    """
    Check current inventory status in Merchant Center.
    
    GET /api/merchant-inventory
    
    Returns: {
        "total_products": int,
        "in_stock": int,
        "out_of_stock": int,
        "last_sync": ISO timestamp,
        "warnings": [list of warnings]
    }
    """
    if not MERCHANT_API_ENABLED or _merchant_client is None:
        return jsonify({"error": "Merchant API not enabled"}), 503
    
    try:
        status = _merchant_client.get_inventory_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/phase-3-info', methods=['GET'])
def phase_3_info():
    """
    Get Phase 3 integration status and information.
    
    GET /api/phase-3-info
    
    Returns: {
        "phase_3_enabled": bool,
        "merchant_api_available": bool,
        "project_id": string or null,
        "merchant_id": string or null,
        "features": {
            "real_time_sync": bool,
            "insights_reporting": bool,
            "inventory_tracking": bool
        }
    }
    """
    from src.merchant_api import MERCHANT_API_AVAILABLE
    
    return jsonify({
        "phase_3_enabled": MERCHANT_API_ENABLED,
        "merchant_api_available": MERCHANT_API_AVAILABLE,
        "project_id": os.getenv("GCP_PROJECT_ID", None),
        "merchant_id": os.getenv("GCP_MERCHANT_ID") or os.getenv("GMC_MERCHANT_ID", None),
        "features": {
            "real_time_sync": MERCHANT_API_ENABLED,
            "insights_reporting": MERCHANT_API_ENABLED,
            "inventory_tracking": MERCHANT_API_ENABLED
        },
        "endpoints": {
            "sync": "POST /api/sync-merchant-api",
            "insights": "GET /api/merchant-insights?days=30",
            "status": "GET /api/merchant-sync-status",
            "inventory": "GET /api/merchant-inventory"
        }
    }), 200


# ===========================================================================
# Phase 4: Native Checkout & AI Agent Support Endpoints
# ===========================================================================

@app.route('/api/native-checkout', methods=['POST'])
def native_checkout_endpoint():
    """
    Execute complete native checkout flow (A2A transaction).
    
    POST /api/native-checkout
    
    Body: {
        "agent_id": "agent-123",
        "user_id": "user-456",
        "items": [{"product_id": "prod-1", "quantity": 2}],
        "payment_method": "paystack",
        "session_id": "ses-789" (optional),
        "metadata": {...}
    }
    
    Returns: {
        "success": bool,
        "order_id": string,
        "transaction_id": string,
        "total": float,
        "estimated_delivery": ISO datetime
    }
    """
    if not PHASE4_ENABLED or not _checkout_service:
        return jsonify({"error": "Phase 4 not enabled"}), 503
    
    try:
        data = request.get_json()
        
        success, result = _checkout_service.native_checkout(
            data['agent_id'],
            data['user_id'],
            data['items'],
            data.get('payment_method', 'paystack'),
            data.get('metadata')
        )
        
        if success and _conversion_tracker:
            # Track conversion
            session_id = data.get('session_id')
            if session_id:
                _conversion_tracker.track_conversion(
                    session_id,
                    result['order_id'],
                    result['total'],
                    len(data['items'])
                )
        
        return jsonify(result), 200 if success else 400
    
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversion/session/start', methods=['POST'])
def start_conversion_session():
    """
    Start tracking user session from AI agent.
    
    POST /api/conversion/session/start
    
    Body: {
        "agent_id": "agent-123",
        "user_id": "user-456",
        "context": {...}
    }
    
    Returns: {
        "session_id": string
    }
    """
    if not PHASE4_ENABLED or not _conversion_tracker:
        return jsonify({"error": "Phase 4 not enabled"}), 503
    
    try:
        data = request.get_json()
        
        session_id = _conversion_tracker.start_session(
            data['agent_id'],
            data['user_id'],
            data.get('context')
        )
        
        return jsonify({"session_id": session_id}), 200
    
    except Exception as e:
        logger.error(f"Session start error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversion/session/<session_id>/stats', methods=['GET'])
def get_session_stats(session_id):
    """
    Get conversion statistics for a session.
    
    GET /api/conversion/session/{session_id}/stats
    
    Returns: {
        "session_id": string,
        "agent_id": string,
        "user_id": string,
        "duration_seconds": float,
        "event_count": int,
        "converted": bool,
        "order_id": string or null,
        "events": [...]
    }
    """
    if not PHASE4_ENABLED or not _conversion_tracker:
        return jsonify({"error": "Phase 4 not enabled"}), 503
    
    try:
        stats = _conversion_tracker.get_session_stats(session_id)
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Session stats error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversion/agent/<agent_id>/metrics', methods=['GET'])
def get_agent_metrics(agent_id):
    """
    Get AI agent performance metrics.
    
    GET /api/conversion/agent/{agent_id}/metrics?days=30
    
    Returns: {
        "agent_id": string,
        "period_days": int,
        "sessions": int,
        "conversions": int,
        "conversion_rate": float,
        "total_revenue": float,
        "avg_order_value": float,
        "events": int
    }
    """
    if not PHASE4_ENABLED or not _conversion_tracker:
        return jsonify({"error": "Phase 4 not enabled"}), 503
    
    try:
        days = request.args.get('days', 30, type=int)
        metrics = _conversion_tracker.get_agent_metrics(agent_id, days)
        return jsonify(metrics), 200
    
    except Exception as e:
        logger.error(f"Agent metrics error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversion/agents/top', methods=['GET'])
def get_top_agents():
    """
    Get top performing agents by conversion rate.
    
    GET /api/conversion/agents/top?limit=10&days=30
    
    Returns: [
        {
            "agent_id": string,
            "sessions": int,
            "conversions": int,
            "conversion_rate": float
        },
        ...
    ]
    """
    if not PHASE4_ENABLED or not _conversion_tracker:
        return jsonify({"error": "Phase 4 not enabled"}), 503
    
    try:
        limit = request.args.get('limit', 10, type=int)
        days = request.args.get('days', 30, type=int)
        agents = _conversion_tracker.get_top_agents(limit, days)
        return jsonify(agents), 200
    
    except Exception as e:
        logger.error(f"Top agents error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/phase-4-info', methods=['GET'])
def phase_4_info():
    """
    Get Phase 4 implementation status.
    
    GET /api/phase-4-info
    
    Returns: {
        "phase_4_enabled": bool,
        "components": {
            "mcp_server": bool,
            "a2a_router": bool,
            "checkout_service": bool,
            "conversion_tracker": bool
        },
        "features": [
            "mcp_tools",
            "native_checkout",
            "a2a_transactions",
            "conversion_tracking"
        ],
        "endpoints": {...},
        "mcp_tools_count": int
    }
    """
    from src.mcp_server import MCPToolRegistry
    
    mcp_registry = MCPToolRegistry() if PHASE4_ENABLED else None
    
    return jsonify({
        "phase_4_enabled": PHASE4_ENABLED,
        "components": {
            "mcp_server": mcp_bp is not None,
            "a2a_router": _a2a_router is not None,
            "checkout_service": _checkout_service is not None,
            "conversion_tracker": _conversion_tracker is not None
        },
        "features": [
            "mcp_tools",
            "native_checkout",
            "a2a_transactions",
            "conversion_tracking"
        ],
        "endpoints": {
            "mcp_tools": "GET /api/mcp/tools",
            "mcp_execute": "POST /api/mcp/execute",
            "checkout": "POST /api/native-checkout",
            "session_start": "POST /api/conversion/session/start",
            "session_stats": "GET /api/conversion/session/{session_id}/stats",
            "agent_metrics": "GET /api/conversion/agent/{agent_id}/metrics",
            "top_agents": "GET /api/conversion/agents/top"
        },
        "mcp_tools_count": len(mcp_registry.get_tools()) if mcp_registry else 0
    }), 200
