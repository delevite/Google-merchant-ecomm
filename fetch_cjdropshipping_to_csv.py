






import os
import requests
import csv
import logging
import time
import schedule
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Securely load your CJdropshipping access token from environment variable
CJ_ACCESS_TOKEN = os.environ.get('CJ_ACCESS_TOKEN')
if not CJ_ACCESS_TOKEN:
    raise RuntimeError("CJ_ACCESS_TOKEN environment variable not set. Please set it in your .env file.")

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
