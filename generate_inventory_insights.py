import csv


def generate_inventory_insights():
    low_stock_products = []
    top_selling_products = []

    with open("feed.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                stock = int(row.get("stock", 0))
                if stock < 10:
                    low_stock_products.append(row)
            except (ValueError, TypeError):
                pass

            try:
                rating = float(row.get("rating", 0))
                if rating >= 4.5:
                    top_selling_products.append(row)
            except (ValueError, TypeError):
                pass

    with open("inventory_insights.txt", "w", encoding="utf-8") as f:
        f.write("--- Inventory Insights ---\n\n")
        f.write("--- Low Stock Products (less than 10 items) ---\n")
        if low_stock_products:
            for product in low_stock_products:
                f.write(f"- {product['title']} (Stock: {product['stock']})\n")
        else:
            f.write("No low stock products found.\n")

        f.write("\n--- Top Selling Products (Rating 4.5+) ---\n")
        if top_selling_products:
            for product in top_selling_products:
                f.write(f"- {product['title']} (Rating: {product['rating']})\n")
        else:
            f.write("No top selling products found.\n")


if __name__ == "__main__":
    generate_inventory_insights()
