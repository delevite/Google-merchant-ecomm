import os
import requests
import csv

def fetch_and_save_cj_feed():
    API_KEY = os.environ.get('CJ_API_KEY')
    if not API_KEY:
        print("Error: CJ_API_KEY not found in environment variables.")
        return

    url = "https://developers.cjdropshipping.com/api/product/list"
    headers = {"CJ-Access-Token": API_KEY}
    params = {'pageNum': 1, 'pageSize': 100}  # Adjust as needed

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if not data.get('data') or not data['data'].get('list'):
            print("No products found in CJ Dropshipping response.")
            return

        products = data['data']['list']
        
        # Define the headers for your CSV file
        headers = [
            'id', 'title', 'image', 'price', 'url', 'description', 
            'brand', 'rating', 'stock', 'category', 'shipping'
        ]

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Define the path to the CSV file relative to the script's directory
        csv_path = os.path.join(script_dir, 'feed.csv')

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
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

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to CJ Dropshipping API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Starting daily CJ Dropshipping inventory sync...")
    fetch_and_save_cj_feed()
    print("Inventory sync finished.")
