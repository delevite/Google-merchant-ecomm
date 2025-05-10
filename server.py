
 
from flask import Flask, send_from_directory, make_response, jsonify, request, redirect, session, render_template_string
from flask_cors import CORS
import os
import csv
import json
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'changeme')  # Set a strong secret in production

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

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password')

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
    
    # Ensure the Flask app runs when this script is executed directly
if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000 ...")
    app.run(debug=True, host="0.0.0.0", port=5000)