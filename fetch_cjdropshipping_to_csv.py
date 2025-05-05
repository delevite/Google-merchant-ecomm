import os
import requests
import csv
import logging
import time
import schedule
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



# Securely load your CJdropshipping email, api_key (password), and refreshToken from environment variables
CJ_EMAIL = os.environ.get('CJ_EMAIL', 'YOUR_EMAIL_HERE')
CJ_API_KEY = os.environ.get('CJ_API_KEY', 'YOUR_API_KEY_HERE')
REFRESH_TOKEN = os.environ.get('CJ_REFRESH_TOKEN', '')

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
            return data['data']['accessToken'], data['data']['refreshToken']
        else:
            raise Exception(f"Failed to get access token: {data.get('message', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Failed to fetch access token: {e}")
        raise

def refresh_access_token(refresh_token):
    url = 'https://developers.cjdropshipping.com/api2.0/v1/authentication/refreshAccessToken'
    payload = {'refreshToken': refresh_token}
    headers = {'Content-Type': 'application/json'}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 200 and data.get('data', {}).get('accessToken'):
            return data['data']['accessToken'], data['data']['refreshToken']
        else:
            raise Exception(f"Failed to refresh access token: {data.get('message', 'Unknown error')}")
    except Exception as e:
        logging.error(f"Failed to refresh access token: {e}")
        raise


# Helper to check if token is expired or invalid (by making a test API call)
def is_token_valid(token):
    test_url = 'https://developers.cjdropshipping.com/api2.0/v1/product/list'
    headers = {'CJ-Access-Token': token, 'Content-Type': 'application/json'}
    params = {'pageNum': 1, 'pageSize': 1}
    try:
        resp = requests.post(test_url, headers=headers, json=params, timeout=10)
        if resp.status_code == 200:
            return True
        # If unauthorized or token expired
        if resp.status_code in (401, 403):
            return False
        # If token expired (CJ API returns code 1600002 for expired token)
        data = resp.json()
        if data.get('code') in (1600001, 1600002):
            return False
        return True
    except Exception as e:
        logging.warning(f"Token validity check failed: {e}")
        return False

# Main token logic: only refresh if token is missing or invalid
def get_valid_access_token():
    # Try refresh token if present
    if REFRESH_TOKEN:
        try:
            access_token, new_refresh_token = refresh_access_token(REFRESH_TOKEN)
            if not is_token_valid(access_token):
                raise Exception("Refreshed token is invalid.")
            # Optionally, update .env with new_refresh_token for next run
            if new_refresh_token != REFRESH_TOKEN:
                with open('.env', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                with open('.env', 'w', encoding='utf-8') as f:
                    found = False
                    for line in lines:
                        if line.startswith('CJ_REFRESH_TOKEN='):
                            f.write(f'CJ_REFRESH_TOKEN={new_refresh_token}\n')
                            found = True
                        else:
                            f.write(line)
                    if not found:
                        f.write(f'CJ_REFRESH_TOKEN={new_refresh_token}\n')
            return access_token
        except Exception as e:
            logging.warning(f"Refresh token failed: {e}")
    # If no refresh token or refresh failed, get new token with email/api_key
    try:
        access_token, new_refresh_token = fetch_access_token(CJ_EMAIL, CJ_API_KEY)
        if not is_token_valid(access_token):
            raise Exception("Fetched token is invalid.")
        # Optionally, update .env with new_refresh_token for next run
        with open('.env', 'a', encoding='utf-8') as f:
            f.write(f'CJ_REFRESH_TOKEN={new_refresh_token}\n')
        return access_token
    except Exception as e:
        raise RuntimeError("CJdropshipping access token could not be fetched or refreshed. Check your credentials and network connection.")

# Get a valid access token for use in all API calls
CJ_ACCESS_TOKEN = get_valid_access_token()

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
    while True:
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
