"""
Add sample e-commerce data to MongoDB for testing
"""

import asyncio
from datetime import datetime, timedelta
import random
from src.database.mongodb import mongodb_client


async def add_sample_data():
    """Add sample orders with items to MongoDB"""
    await mongodb_client.connect()
    db = mongodb_client.database

    print("Adding sample data to MongoDB...")

    # Sample products
    products = [
        {"name": "Safety Helmet", "price": 25.99, "category": "Safety Equipment", "sku": "SH-001"},
        {"name": "Safety Gloves", "price": 15.99, "category": "Safety Equipment", "sku": "SG-002"},
        {"name": "Safety Boots", "price": 89.99, "category": "Footwear", "sku": "SB-003"},
        {"name": "High-Vis Jacket", "price": 45.99, "category": "Clothing", "sku": "HV-004"},
        {"name": "Safety Goggles", "price": 12.99, "category": "Eye Protection", "sku": "SG-005"}
    ]

    # Update some orders with items
    orders = await db.order.find().limit(10).to_list(length=10)

    for i, order in enumerate(orders):
        # Generate random items for the order
        num_items = random.randint(1, 3)
        items = []
        total_amount = 0

        for j in range(num_items):
            product = random.choice(products)
            quantity = random.randint(1, 5)
            item_total = product["price"] * quantity

            items.append({
                "product_id": f"prod_{j+1}",
                "product_name": product["name"],
                "product_sku": product["sku"],
                "category": product["category"],
                "quantity": quantity,
                "unit_price": product["price"],
                "total_price": item_total
            })
            total_amount += item_total

        # Update order with items and correct total
        update_data = {
            "$set": {
                "items": items,
                "total_amount": round(total_amount, 2),
                "status": random.choice(["completed", "fulfilled", "shipped"]),
                "shop_id": "10",  # Add shop_id
                "order_date": datetime.now() - timedelta(days=random.randint(0, 30))
            }
        }

        result = await db.order.update_one(
            {"_id": order["_id"]},
            update_data
        )

        if result.modified_count > 0:
            print(f"Updated order {i+1} with {len(items)} items, total: ${total_amount:.2f}")

    # Add shop_id to products
    await db.product.update_many(
        {},
        {"$set": {"shop_id": "10"}}
    )

    # Add shop_id to customers
    await db.customer.update_many(
        {},
        {"$set": {"shop_id": "10"}}
    )

    print("\nSample data added successfully!")

    # Verify the data
    orders_with_items = await db.order.count_documents({"items": {"$ne": []}})
    orders_with_shop = await db.order.count_documents({"shop_id": "10"})

    print(f"Orders with items: {orders_with_items}")
    print(f"Orders with shop_id: {orders_with_shop}")


if __name__ == "__main__":
    asyncio.run(add_sample_data())