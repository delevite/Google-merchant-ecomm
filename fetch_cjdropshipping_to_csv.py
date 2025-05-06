
import os
import requests
import csv
import logging
import time
import schedule
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()




# Securely load your CJdropshipping email, api_key (password), refreshToken, accessToken, and expiry from environment variables
def get_env_var(name, default=''):
    return os.environ.get(name, default)

def set_env_var(name, value):
    # Update or append the variable in .env
    with open('.env', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f'{name}='):
            lines[i] = f'{name}={value}\n'
            found = True
            break
    if not found:
        lines.append(f'{name}={value}\n')
    with open('.env', 'w', encoding='utf-8') as f:
        f.writelines(lines)

def get_env():
    return {
        'email': get_env_var('CJ_EMAIL', 'YOUR_EMAIL_HERE'),
        'api_key': get_env_var('CJ_API_KEY', 'YOUR_API_KEY_HERE'),
        'access_token': get_env_var('CJ_ACCESS_TOKEN', ''),
        'access_token_expiry': get_env_var('CJ_ACCESS_TOKEN_EXPIRY', ''),
    }


def fetch_access_token(email, api_key):
    url = 'https://developers.cjdropshipping.com/api2.0/v1/authentication/getAccessToken'
    payload = {
        'email': email,
        'password': api_key
    }
    headers = {'Content-Type': 'application/json'}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 200 and data.get('data', {}).get('accessToken'):
            access_token = data['data']['accessToken']
            expiry = data['data'].get('accessTokenExpiryDate')
            set_env_var('CJ_ACCESS_TOKEN', access_token)
            if expiry:
                set_env_var('CJ_ACCESS_TOKEN_EXPIRY', expiry)
            return access_token, expiry
        else:
            raise Exception(f"Failed to get access token: {data.get('message', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Failed to fetch access token: {e}")
        raise


# Helper to check if token is expired or invalid (by making a test API call)

def is_token_expired(expiry_str):
    if not expiry_str:
        return True
    try:
        # Example: "2021-08-18T09:16:33+08:00"
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        # Add a buffer of 2 minutes
        return datetime.now(expiry.tzinfo) + timedelta(minutes=2) > expiry
    except Exception:
        return True

# Main token logic: only refresh if token is missing or invalid

# Main token logic: only refresh if token is expired

# Always fetch a new access token using email and API key (never use refresh token)
def get_fresh_access_token():
    env = get_env()
    try:
        access_token, expiry = fetch_access_token(env['email'], env['api_key'])
        return access_token
    except Exception as e:
        raise RuntimeError("CJdropshipping access token could not be fetched. Check your credentials and network connection.")

CJ_ACCESS_TOKEN = get_fresh_access_token()

API_URL = 'https://developers.cjdropshipping.com/api2.0/v1/product/list'
CSV_FILE = 'feed.csv'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('fetch_cjdropshipping.log'), logging.StreamHandler()]
)

# Field mapping: CSV column -> (lambda product: value)

# Custom category logic: assign 'Health, Beauty and Skincare Products' if product matches, else use CJ category
def custom_category(p):
    # You can adjust these keywords as needed
    keywords = ['health', 'beauty', 'skincare']
    name = (p.get('productNameEn', '') or '').lower()
    desc = (p.get('productName', '') or '').lower()
    cat = (p.get('categoryName', '') or '').lower()
    if any(kw in name or kw in desc or kw in cat for kw in keywords):
        return 'Health, Beauty and Skincare Products'
    return p.get('categoryName', '')

FIELD_MAPPING = {
    'title': lambda p: p.get('productNameEn', ''),
    'image': lambda p: p.get('productImage', ''),
    'price': lambda p: p.get('sellPrice', ''),
    'url': lambda p: f"https://app.cjdropshipping.com/product-detail/{p.get('pid', '')}",
    'description': lambda p: ', '.join(p.get('productName', [])) if isinstance(p.get('productName'), list) else p.get('productName', ''),
    'brand': lambda p: '',  # Not provided by CJ API
    'rating': lambda p: '',  # Not provided by CJ API
    'stock': lambda p: '',  # Not provided by CJ API
    'category': custom_category,
    'shipping': lambda p: ''  # Not provided by CJ API
}
CSV_FIELDS = list(FIELD_MAPPING.keys())

def fetch_products(page_num=1, page_size=50):
    headers = {
        'CJ-Access-Token': CJ_ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    params = {
        'pageNum': page_num,
        'pageSize': page_size
    }
    try:
        # CJdropshipping product list endpoint expects GET, not POST
        response = requests.get(API_URL, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get('code') != 200 or not data.get('data') or not data['data'].get('list'):
            raise Exception(f"API error: {data.get('message', 'Unknown error')}")
        return data['data']['list']
    except Exception as e:
        logging.error(f"Failed to fetch products (page {page_num}): {e}")
        return []

def write_to_csv(products):
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for p in products:
                row = {col: func(p) for col, func in FIELD_MAPPING.items()}
                writer.writerow(row)
        logging.info(f"Wrote {len(products)} products to {CSV_FILE}")
    except Exception as e:
        logging.error(f"Failed to write to CSV: {e}")

def fetch_and_update():
    logging.info("Starting product fetch...")
    all_products = []
    page_num = 1
    page_size = 50
    max_offset = 6000
    while True:
        offset = (page_num - 1) * page_size
        if offset >= max_offset:
            logging.info(f"Reached CJdropshipping API max offset of {max_offset}. Stopping fetch.")
            break
        products = fetch_products(page_num=page_num, page_size=page_size)
        if not products:
            break
        all_products.extend(products)
        if len(products) < page_size:
            break
        page_num += 1
    if all_products:
        write_to_csv(all_products)
        logging.info(f"Fetched {len(all_products)} products.")
    else:
        logging.warning("No products fetched.")

def main():
    # Schedule to run every 6 hours (customize as needed)
    schedule.every(6).hours.do(fetch_and_update)
    logging.info("Scheduled CJdropshipping fetch every 6 hours.")
    fetch_and_update()  # Run once at startup
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()
