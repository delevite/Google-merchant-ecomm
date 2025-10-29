import csv
import json
import re
import os


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
                ]
                return ", ".join(cleaned_data)
        except json.JSONDecodeError:
            return value
    return value


def generate_gmc_feed(input_csv_path, output_tsv_path, currency="USD"):
    """
    Generates a Google Merchant Center product feed from a CSV file.

    Args:
        input_csv_path (str): Path to the input CSV file (feed.csv).
        output_tsv_path (str): Path to the output TSV file for GMC.
        currency (str): The currency to use for the price.
    """
    gmc_products = []

    with open(input_csv_path, mode="r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            # Extract product ID from URL
            product_id_match = re.search(r"product-detail/(\d+)", row.get("url", ""))
            product_id = (
                product_id_match.group(1) if product_id_match else row.get("title", "")
            )

            # Handle price range (take the lower value) and format with currency
            price_str = row.get("price", "0").strip()
            if " -- " in price_str:
                price_value = float(price_str.split(" -- ")[0])
            else:
                try:
                    price_value = float(price_str)
                except ValueError:
                    price_value = 0.0

            formatted_price = f"{price_value:.2f} {currency}"

            # Determine availability
            try:
                stock_level = int(row.get("stock", "0"))
                availability = "in stock" if stock_level > 0 else "out of stock"
            except (ValueError, TypeError):
                availability = "out of stock"  # Default if stock is not a valid number

            # Clean up description, brand, and category fields
            description = clean_value(row.get("description", ""))
            brand = clean_value(row.get("brand", ""))
            category = clean_value(row.get("category", ""))

            # Construct GMC product entry
            gmc_product = {
                "id": product_id,
                "title": row.get("title", "").strip(),
                "description": description,
                "link": row.get("url", "").strip(),
                "image_link": row.get("image", "").strip(),
                "price": formatted_price,
                "availability": availability,
                "condition": "new",
                "brand": brand if brand else "Generic",  # Default brand if empty
                "google_product_category": category,  # Use existing category, might need manual mapping later
                "shipping": row.get(
                    "shipping", f"0.00 {currency}"
                ),  # Default shipping if empty
            }
            gmc_products.append(gmc_product)

    # Write to TSV file
    if gmc_products:
        fieldnames = gmc_products[0].keys()
        with open(output_tsv_path, mode="w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(gmc_products)
        print(f"Successfully generated GMC feed to {output_tsv_path}")
    else:
        print("No products found to generate feed.")


if __name__ == "__main__":
    input_csv = "feed.csv"
    output_tsv = "gmc_product_feed.tsv"
    generate_gmc_feed(input_csv, output_tsv, currency="NGN")
