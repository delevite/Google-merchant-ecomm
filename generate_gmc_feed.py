
import csv
import json
import re

def generate_gmc_feed(input_csv_path, output_tsv_path):
    """
    Generates a Google Merchant Center product feed from a CSV file.

    Args:
        input_csv_path (str): Path to the input CSV file (feed.csv).
        output_tsv_path (str): Path to the output TSV file for GMC.
    """
    gmc_products = []
    
    with open(input_csv_path, mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            # Extract product ID from URL
            product_id_match = re.search(r'product-detail/(\d+)', row['url'])
            product_id = product_id_match.group(1) if product_id_match else ''

            # Handle price range (take the lower value) and format with currency
            price_str = row['price'].strip()
            if ' -- ' in price_str:
                price_value = float(price_str.split(' -- ')[0])
            else:
                price_value = float(price_str)
            
            formatted_price = f"{price_value:.2f} NGN" # Assuming Nigerian Naira

            # Determine availability
            # Assuming 'stock' is a numeric string, convert to int for comparison
            try:
                stock_level = int(row.get('stock', '0'))
                availability = 'in stock' if stock_level > 0 else 'out of stock'
            except ValueError:
                availability = 'out of stock' # Default if stock is not a valid number

            # Clean up description field (remove JSON-like array string if present)
            description = row['description'].strip()
            if description.startswith('[') and description.endswith(']'):
                try:
                    # Attempt to parse as JSON and take the first element, or join if multiple
                    desc_list = json.loads(description)
                    description = desc_list[0] if desc_list else ''
                except json.JSONDecodeError:
                    # If not valid JSON, just use the raw string
                    pass
            
            # Construct GMC product entry
            gmc_product = {
                'id': product_id,
                'title': row['title'].strip(),
                'description': description,
                'link': row['url'].strip(),
                'image_link': row['image'].strip(),
                'price': formatted_price,
                'availability': availability,
                'condition': 'new',
                'brand': row['brand'].strip() if row['brand'] else 'Generic', # Default brand if empty
                'google_product_category': row['category'].strip() if row['category'] else '', # Use existing category, might need manual mapping later
                'shipping': row['shipping'].strip() if row['shipping'] else '0.00 NGN', # Default shipping if empty
            }
            gmc_products.append(gmc_product)

    # Write to TSV file
    if gmc_products:
        fieldnames = gmc_products[0].keys()
        with open(output_tsv_path, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(gmc_products)
        print(f"Successfully generated GMC feed to {output_tsv_path}")
    else:
        print("No products found to generate feed.")

if __name__ == "__main__":
    input_csv = 'C:/Users/Delev/OneDrive/Desktop/Google merchant ecomm/feed.csv'
    output_tsv = 'C:/Users/Delev/OneDrive/Desktop/Google merchant ecomm/gmc_product_feed.tsv'
    generate_gmc_feed(input_csv, output_tsv)
