
 
from flask import Flask, send_from_directory, make_response, jsonify, request, redirect, session, render_template_string
from flask_cors import CORS
import os
import csv
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter


app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'changeme')  # Set a strong secret in production

# Load environment variables from a .env file
load_dotenv()

# --- Gemini API Setup ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
if not os.getenv("GEMINI_API_KEY"):
    print("Warning: GEMINI_API_KEY environment variable not set.")

# Serve static legal/info pages so nav links work locally
@app.route('/about.html')
def about():
    return send_from_directory(os.getcwd(), 'about.html')

@app.route('/terms.html')
def terms():
    return send_from_directory(os.getcwd(), 'terms.html')

@app.route('/privacy.html')
def privacy():
    return send_from_directory(os.getcwd(), 'privacy.html')

@app.route('/contact.html')
def contact():
    return send_from_directory(os.getcwd(), 'contact.html')

# Serve the generated blog index from /site/blog.html for /blog.html
@app.route('/blog.html')
def blog_index():
    return send_from_directory(os.path.join(os.getcwd(), 'site'), 'blog.html')

@app.route('/2025-trending-products.html')
def trending_products():
    return send_from_directory(os.path.join(os.getcwd(), 'site'), '2025-trending-products.html')

@app.route('/tag-products.html')
def tag_products():
    return send_from_directory(os.path.join(os.getcwd(), 'site'), 'tag-products.html')
# Generic route for other tag pages, e.g., /tag-trending.html or /tag-2025.html
# This will serve files like site/tag-trending.html or site/tag-2025.html
@app.route('/tag-<string:tag_slug>.html')
def serve_tag_page_generic(tag_slug):
    return send_from_directory(os.path.join(os.getcwd(), 'site'), f'tag-{tag_slug}.html')

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password')

# Serve static files from the 'site' directory if requested with /site/ prefix
# This will handle requests like /site/tag-trending.html
@app.route('/site/<path:filename>')
def serve_from_site_prefixed(filename):
    # send_from_directory helps prevent directory traversal attacks.
    return send_from_directory(os.path.join(os.getcwd(), 'site'), filename)

UPLOAD_HISTORY_FILE = os.path.join(os.getcwd(), 'upload_history.json')

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response

@app.route('/')
def index():
    # Serve the landing page HTML
    return send_from_directory(os.getcwd(), 'landing_page.html')

@app.route('/feed.csv')
def feed():
    # Serve the CSV product feed
    return send_from_directory(os.getcwd(), 'feed.csv')

def fetch_cj_products():
    products = []
    with open(os.path.join(os.getcwd(), 'feed.csv'), newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            products.append({
                'title': row.get('title', ''),
                'title_zh': row.get('title_zh', ''),
                'title_optimized': row.get('title_optimized', ''),
                'image': row.get('image', ''),
                'price': row.get('price', ''),
                'url': row.get('url', ''),
                'description': row.get('description', ''),
                'description_zh': row.get('description_zh', ''),
                'brand': row.get('brand', ''),
                'rating': row.get('rating', ''),
                'stock': row.get('stock', ''),
                'category': row.get('category', ''),
                'shipping': row.get('shipping', '')
            })
    return products

@app.route('/products')
def get_products():
    search = request.args.get('search', '').strip().lower()
    category = request.args.get('category', '').strip()
    min_price = float(request.args.get('min_price', 0) or 0)
    max_price = float(request.args.get('max_price', float('inf')) or float('inf'))
    all_products = fetch_cj_products()
    filtered = []
    for p in all_products:
        try:
            price = float(p['price'])
        except Exception:
            price = 0
        # Search filter
        matches_search = (
            not search or
            search in p.get('title', '').lower() or
            search in p.get('description', '').lower() or
            search in p.get('brand', '').lower() or
            search in p.get('category', '').lower()
        )
        if price >= min_price and price <= max_price and matches_search:
            if not category or category.lower() in p['category'].lower():
                filtered.append(p)
    return jsonify(filtered)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin')
        return render_template_string('<p class="text-red-600">Invalid credentials</p>' + LOGIN_FORM)
    return render_template_string(LOGIN_FORM)

LOGIN_FORM = '''
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
'''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

@app.route('/admin')
def admin_page():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    return send_from_directory(os.getcwd(), 'admin.html')

def log_upload(filename, username):
    entry = {
        'filename': filename,
        'username': username,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    if os.path.exists(UPLOAD_HISTORY_FILE):
        with open(UPLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []
    history.append(entry)
    with open(UPLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

@app.route('/admin/upload', methods=['POST'])
def upload_feed():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    if 'csvFile' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['csvFile']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only CSV files are allowed'}), 400
    filename = secure_filename('feed.csv')
    file.save(os.path.join(os.getcwd(), filename))
    log_upload(filename, session.get('admin_user', 'admin'))
    return jsonify({'message': 'Feed uploaded successfully!'}), 200

@app.route('/admin/history')
def upload_history():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    if os.path.exists(UPLOAD_HISTORY_FILE):
        with open(UPLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []
    return jsonify(history)

@app.route('/admin/change-credentials', methods=['POST'])
def change_credentials():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    new_user = data.get('username')
    new_pass = data.get('password')
    if not new_user or not new_pass:
        return jsonify({'error': 'Username and password required'}), 400
    # Save to a file for persistence (in production, use a secure method)
    with open(os.path.join(os.getcwd(), 'admin_creds.json'), 'w', encoding='utf-8') as f:
        json.dump({'username': new_user, 'password': new_pass}, f)
    global ADMIN_USERNAME, ADMIN_PASSWORD
    ADMIN_USERNAME = new_user
    ADMIN_PASSWORD = new_pass
    return jsonify({'message': 'Credentials updated. Please log in again.'})

@app.before_request
def load_admin_creds():
    creds_path = os.path.join(os.getcwd(), 'admin_creds.json')
    global ADMIN_USERNAME, ADMIN_PASSWORD
    if os.path.exists(creds_path):
        with open(creds_path, 'r', encoding='utf-8') as f:
            creds = json.load(f)
            ADMIN_USERNAME = creds.get('username', ADMIN_USERNAME)
            ADMIN_PASSWORD = creds.get('password', ADMIN_PASSWORD)

@app.route('/admin/products', methods=['GET', 'POST', 'DELETE'])
def manage_products():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    if request.method == 'GET':
        return jsonify(fetch_cj_products())
    elif request.method == 'POST':
        # Add or update a product
        data = request.json
        products = fetch_cj_products()
        # If title exists, update; else, add
        found = False
        for p in products:
            if p['title'] == data.get('title'):
                p.update(data)
                found = True
                break
        if not found:
            products.append(data)
        # Write back to CSV
        with open(os.path.join(os.getcwd(), 'feed.csv'), 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=products[0].keys())
            writer.writeheader()
            writer.writerows(products)
        return jsonify({'message': 'Product saved.'})
    elif request.method == 'DELETE':
        # Delete a product by title
        title = request.args.get('title')
        products = fetch_cj_products()
        products = [p for p in products if p['title'] != title]
        if products:
            with open(os.path.join(os.getcwd(), 'feed.csv'), 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=products[0].keys())
                writer.writeheader()
                writer.writerows(products)
        return jsonify({'message': 'Product deleted.'})

# --- Implementation of Task #4: AI Product Tag Generator ---
@app.route('/generate-tags', methods=['POST'])
def generate_tags():
    """
    Accepts a product title and description and returns AI-generated SEO tags.
    Expects a JSON payload with 'title' and 'description' keys.
    """
    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({"error": "Gemini API key is not configured on the server."}), 500

    data = request.get_json()
    if not data or 'title' not in data or 'description' not in data:
        return jsonify({"error": "Missing 'title' or 'description' in request body"}), 400

    product_title = data['title']
    product_description = data['description']

    try:
        # Initialize the Gemini Pro model
        model = genai.GenerativeModel('gemini-pro')

        # Example prompt as per your GEMINI.md
        prompt = f"Generate 5-7 SEO-friendly product tags for a product with the title '{product_title}' and description '{product_description}'. Return the tags as a single comma-separated string."

        response = model.generate_content(prompt)

        # The response from Gemini is in response.text
        tags_string = response.text.strip()
        tags_list = [tag.strip() for tag in tags_string.split(',') if tag.strip()]

        return jsonify({"product_title": product_title, "generated_tags": tags_list})

    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An error occurred with the AI service: {str(e)}"}), 503

# --- Vendor Management (Task #5) ---
VENDORS_FILE = os.path.join(os.getcwd(), 'data', 'vendors.json')

def load_vendors():
    data_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    if not os.path.exists(VENDORS_FILE):
        return []
    with open(VENDORS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_vendor(username):
    vendors = load_vendors()
    for vendor in vendors:
        if vendor['username'] == username:
            return vendor
    return None

VENDOR_LOGIN_FORM = '''
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
'''

@app.route('/vendor/login', methods=['GET', 'POST'])
def vendor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        vendor = get_vendor(username)
        if vendor and check_password_hash(vendor['password_hash'], password):
            session['vendor_logged_in'] = True
            session['vendor_id'] = vendor['id']
            return redirect('/vendor/dashboard')
        return render_template_string('<p class="text-red-600">Invalid credentials</p>' + VENDOR_LOGIN_FORM)
    return render_template_string(VENDOR_LOGIN_FORM)

@app.route('/vendor/logout')
def vendor_logout():
    session.pop('vendor_logged_in', None)
    session.pop('vendor_id', None)
    return redirect('/vendor/login')

@app.route('/vendor/dashboard')
def vendor_dashboard():
    if not session.get('vendor_logged_in'):
        return redirect('/vendor/login')
    vendor_id = session.get('vendor_id', 'Unknown')
    # A simple dashboard page for the vendor
    DASHBOARD_HTML = f'''
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
      <a href="/vendor/logout" class="text-blue-600 hover:underline mt-8 inline-block">Logout</a>
    </body>
    </html>
    '''
    return render_template_string(DASHBOARD_HTML)

# --- PDF Invoice Generation (Task #6) ---
INVOICES_DIR = os.path.join(os.getcwd(), 'invoices')

def generate_invoice_pdf(order_details):
    """Generates a PDF invoice for a given order."""
    if not os.path.exists(INVOICES_DIR):
        os.makedirs(INVOICES_DIR)

    order_id = order_details['id']
    file_path = os.path.join(INVOICES_DIR, f"invoice_{order_id}.pdf")
    
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(1 * inch, height - 1 * inch, "INVOICE")
    c.setFont("Helvetica", 12)
    c.drawString(1 * inch, height - 1.5 * inch, f"Order ID: {order_id}")
    c.drawString(1 * inch, height - 1.7 * inch, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    c.line(1 * inch, height - 3.6 * inch, width - 1 * inch, height - 3.6 * inch)
    y_pos = height - 3.9 * inch
    for item in order_details.get('items', []):
        c.drawString(1 * inch, y_pos, item.get('name', ''))
        c.drawString(6.75 * inch, y_pos, f"${item.get('price', 0) * item.get('quantity', 1):.2f}")
        y_pos -= 0.3 * inch

    c.line(1 * inch, y_pos + 0.1 * inch, width - 1 * inch, y_pos + 0.1 * inch)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(5 * inch, y_pos - 0.3 * inch, "Total:")
    c.drawString(6.5 * inch, y_pos - 0.3 * inch, f"${order_details.get('total', 0):.2f}")

    c.save()

@app.route('/order/create', methods=['POST'])
def create_order():
    """A mock endpoint to simulate creating an order and generating an invoice."""
    data = request.get_json() or {}
    items = data.get('items', [{"name": "Sample Product", "price": 19.99, "quantity": 2}])
    total_price = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
    order_id = str(uuid.uuid4())[:8]
    order_details = {"id": order_id, "items": items, "total": total_price}
    generate_invoice_pdf(order_details)
    invoice_url = f"/invoices/invoice_{order_id}.pdf"
    return jsonify({"message": "Order created", "order_id": order_id, "invoice_url": invoice_url})

@app.route('/invoices/<path:filename>')
def download_invoice(filename):
    """Serves a generated invoice file for download."""
    return send_from_directory(INVOICES_DIR, filename, as_attachment=True)
    
if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000 ...")
    app.run(debug=True, host="0.0.0.0", port=5000)
