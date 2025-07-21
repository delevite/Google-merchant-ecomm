
 
import requests
from flask import Flask, send_from_directory, make_response, jsonify, request, redirect, session, render_template_string
from flask_cors import CORS
import os
import csv
import json
from datetime import datetime
from werkzeug.utils import secure_filename, generate_password_hash, check_password_hash
import hmac
import hashlib
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'changeme')  # Set a strong secret in production

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

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

@app.route('/product')
def get_product_detail():
    title = request.args.get('title')
    if not title:
        return jsonify({'error': 'Product title is required'}), 400

    products = fetch_cj_products()
    for product in products:
        if product.get('title') == title:
            return jsonify(product)
    
    return jsonify({'error': 'Product not found'}), 404

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return render_template_string('<p class="text-red-600">Email and password are required</p>' + SIGNUP_FORM)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template_string('<p class="text-red-600">Email already registered</p>' + SIGNUP_FORM)

        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect('/login')
    return render_template_string(SIGNUP_FORM)

SIGNUP_FORM = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sign Up</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet"/>
</head>
<body class="bg-gray-50 font-sans min-h-screen flex flex-col">
  <main class="flex-1 flex flex-col items-center justify-center">
    <form method="POST" class="bg-white p-8 rounded shadow-md w-full max-w-md mt-8">
      <h2 class="text-xl font-bold mb-4">Sign Up</h2>
      <input type="email" name="email" placeholder="Email" class="mb-4 p-2 border rounded w-full" required />
      <input type="password" name="password" placeholder="Password" class="mb-6 p-2 border rounded w-full" required />
      <button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 w-full">Sign Up</button>
      <p class="mt-4 text-center">Already have an account? <a href="/login" class="text-blue-600 hover:underline">Login here</a></p>
    </form>
  </main>
</body>
</html>
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            if user.is_admin:
                return redirect('/admin')
            else:
                return redirect('/dashboard') # Redirect to a user dashboard
        return render_template_string('<p class="text-red-600">Invalid email or password</p>' + LOGIN_FORM)
    return render_template_string(LOGIN_FORM)

LOGIN_FORM = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Login</title>
  <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet"/>
</head>
<body class="bg-gray-50 font-sans min-h-screen flex flex-col">
  <main class="flex-1 flex flex-col items-center justify-center">
    <form method="POST" class="bg-white p-8 rounded shadow-md w-full max-w-md mt-8">
      <h2 class="text-xl font-bold mb-4">Login</h2>
      <input type="email" name="email" placeholder="Email" class="mb-4 p-2 border rounded w-full" required />
      <input type="password" name="password" placeholder="Password" class="mb-6 p-2 border rounded w-full" required />
      <button type="submit" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 w-full">Login</button>
      <p class="mt-4 text-center">Don't have an account? <a href="/signup" class="text-blue-600 hover:underline">Sign Up here</a></p>
    </form>
  </main>
</body>
</html>
'''

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    return redirect('/login')

@app.route('/admin')
def admin_page():
    if not session.get('is_admin'):
        return redirect('/login')
    return send_from_directory(os.getcwd(), 'admin.html')

@app.route('/dashboard')
def dashboard_page():
    if not session.get('user_id'):
        return redirect('/login')
    # This is a placeholder for the user dashboard.
    # You would typically render a dashboard.html template here.
    return "<h1>Welcome to your Dashboard!</h1><p>You are logged in as a regular user.</p><p><a href="/logout">Logout</a></p>"


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
    if not session.get('is_admin'):
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
    if not session.get('is_admin'):
        return redirect('/admin/login')
    if os.path.exists(UPLOAD_HISTORY_FILE):
        with open(UPLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []
    return jsonify(history)





@app.route('/admin/products', methods=['GET', 'POST', 'DELETE'])
def manage_products():
    if not session.get('is_admin'):
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

@app.route('/submit-order', methods=['POST'])
def submit_order():
    data = request.json
    if not data or not data.get('items'):
        return jsonify({'error': 'Invalid order data'}), 400

    order = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'status': 'Processing',  # Initial status
        'fulfillment_status': 'Pending',
        'customer': data.get('customer', {}),
        'items': data.get('items', []),
        'total': data.get('total', 0),
        'payment_reference': data.get('payment_reference', '')
    }

    log_order(order)
    return jsonify({'message': 'Order received', 'order': order}), 201

def log_order(order_data):
    orders_file = os.path.join(os.getcwd(), 'orders.json')
    orders = []
    if os.path.exists(orders_file):
        with open(orders_file, 'r', encoding='utf-8') as f:
            try:
                orders = json.load(f)
            except json.JSONDecodeError:
                pass  # File is empty or corrupt, start fresh
    orders.append(order_data)
    with open(orders_file, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2)

@app.route('/paystack/webhook', methods=['POST'])
def paystack_webhook():
    # Get the signature from the header
    paystack_signature = request.headers.get('x-paystack-signature')
    
    # Get the request body
    payload = request.data
    
    # Your Paystack secret key
    PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')

    if not PAYSTACK_SECRET_KEY:
        print("Error: PAYSTACK_SECRET_KEY not found in environment variables.")
        return jsonify({'status': 'error', 'message': 'Server configuration error'}), 500

    # Verify the webhook signature
    hash = hmac.new(PAYSTACK_SECRET_KEY.encode('utf-8'), payload, hashlib.sha512).hexdigest()

    if hash != paystack_signature:
        # Signature is not valid, ignore the request
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 401

    # If the signature is valid, process the event
    event_data = json.loads(payload)
    
    if event_data['event'] == 'charge.success':
        reference = event_data['data']['reference']
        
        # Update the order status in orders.json
        orders_file = os.path.join(os.getcwd(), 'orders.json')
        orders = []
        if os.path.exists(orders_file):
            with open(orders_file, 'r', encoding='utf-8') as f:
                try:
                    orders = json.load(f)
                except json.JSONDecodeError:
                    pass # File is empty or corrupt

        for order in orders:
            if order.get('payment_reference') == reference:
                order['status'] = 'Paid'
                order['verified_by'] = 'webhook'
                order['paid_amount'] = event_data['data']['amount'] / 100 # Amount is in kobo
                order['payment_time'] = event_data['data']['paid_at']
                break

        with open(orders_file, 'w', encoding='utf-8') as f:
            json.dump(orders, f, indent=2)

    return jsonify({'status': 'success'}), 200

@app.route('/sitemap.xml')
def sitemap():
    # Base URL for your domain
    base_url = "https://yourdomain.com" # Replace with your actual domain

    # Static pages
    static_pages = [
        "/",
        "/about.html",
        "/contact.html",
        "/privacy.html",
        "/terms.html",
        "/blog.html"
    ]

    # Dynamically add product pages
    products = fetch_cj_products()
    product_pages = [f"/product?title={p['title']}" for p in products if p.get('title')]

    # Combine all URLs
    all_urls = static_pages + product_pages

    # Generate XML sitemap content
    xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'''
    for url_path in all_urls:
        full_url = f"{base_url}{url_path}"
        xml_content += f'''
    <url>
        <loc>{full_url}</loc>
        <lastmod>{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.7</priority>
    </url>'''
    xml_content += '''
</urlset>'''

    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/admin/sync-cj')
def sync_cj_feed_route():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    success, message = fetch_and_save_cj_feed()
    
    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'error': message}), 500

    
# Generic route for individual blog posts, e.g., /dropshipping-tips.html
@app.route('/<string:slug>.html')
def serve_blog_post(slug):
    return send_from_directory(os.path.join(os.getcwd(), 'site'), f'{slug}.html')

# The tag_products route was already defined earlier, and this one was incomplete.
# If you intended to redefine it or add new logic, ensure it's correctly placed and has a body.
# For now, I'm assuming the earlier definition is the one you want to keep.
# If this was a duplicate or an accidental addition, it can be removed.

def fetch_and_save_cj_feed():
    API_KEY = os.environ.get('CJ_API_KEY')
    if not API_KEY:
        print("Error: CJ_API_KEY not found in environment variables.")
        return False, "CJ_API_KEY not configured"

    url = "https://developers.cjdropshipping.com/api/product/list"
    headers = {"CJ-Access-Token": API_KEY}
    params = {'pageNum': 1, 'pageSize': 100}  # Adjust as needed

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if not data.get('data') or not data['data'].get('list'):
            print("No products found in CJ Dropshipping response.")
            return True, "No products found"

        products = data['data']['list']
        
        # Define the headers for your CSV file
        headers = [
            'id', 'title', 'image', 'price', 'url', 'description', 
            'brand', 'rating', 'stock', 'category', 'shipping'
        ]

        with open(os.path.join(os.getcwd(), 'feed.csv'), 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            for product in products:
                writer.writerow({
                    'id': product.get('pid', ''),
                    'title': product.get('productNameEn', ''),
                    'image': product.get('productImage', ''),
                    'price': product.get('sellPrice', '0.00'),
                    'url': f"https://cjdropshipping.com/product/{product.get('pid', '')}.html",
                    'description': product.get('description', ''),
                    'brand': 'CJ Dropshipping',  # Placeholder
                    'rating': '4.5',  # Placeholder
                    'stock': product.get('totalStock', '0'),
                    'category': product.get('categoryName', ''),
                    'shipping': '5.00'  # Placeholder
                })
        
        print(f"Successfully fetched and saved {len(products)} products to feed.csv.")
        return True, f"Successfully fetched {len(products)} products."

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to CJ Dropshipping API: {e}")
        return False, f"API request failed: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False, f"An unexpected error occurred: {e}"

    @app.route('/gmc-feed.xml')
def gmc_feed():
    products = fetch_cj_products()
    xml_content = '''<?xml version="1.0"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">
  <channel>
    <title>Your Store Name</title>
    <link>https://yourdomain.com</link>
    <description>Your store's description</description>'''

    for p in products:
        product_id = p.get('id') or p['url'].split('/')[-1].split('.')[0] # Use 'id' or extract from URL
        title = p.get('title', '')
        description = p.get('description', '')
        link = p.get('url', '')
        image_link = p.get('image', '')
        
        # Handle price variations (e.g., "4.86 -- 6.22")
        price_str = p.get('price', '0.00').split(' ')[0] # Take the first price if a range
        try:
            price = float(price_str)
        except ValueError:
            price = 0.00
        formatted_price = f"{price:.2f} NGN" # Assuming Nigerian Naira

        availability = "in stock" if int(p.get('stock', 0)) > 0 else "out of stock"
        brand = p.get('brand', 'Generic')
        category = p.get('category', 'Apparel & Accessories') # Default category

        xml_content += f'''
    <item>
      <g:id>{product_id}</g:id>
      <g:title>{title}</g:title>
      <g:description>{description}</g:description>
      <g:link>{link}</g:link>
      <g:image_link>{image_link}</g:image_link>
      <g:price>{formatted_price}</g:price>
      <g:availability>{availability}</g:availability>
      <g:brand>{brand}</g:brand>
      <g:condition>new</g:condition>
      <g:google_product_category>{category}</g:google_product_category>
      <g:identifier_exists>FALSE</g:identifier_exists>
    </item>'''

    xml_content += '''
  </channel>
</rss>'''

    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response

# Ensure the Flask app runs when this script is executed directly
if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000 ...")
    app.run(debug=True, host="0.0.0.0", port=5000)
