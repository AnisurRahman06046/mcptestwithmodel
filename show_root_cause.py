#!/usr/bin/env python3
"""
Show the root cause of the issue
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.universal_query_builder import universal_query_builder
from src.database.mongodb import mongodb_client


async def show_root_cause():
    print("=" * 70)
    print("ROOT CAUSE ANALYSIS: Why LLM Returns 0 Active Products")
    print("=" * 70)

    await mongodb_client.connect()

    # Fetch the products data
    products_data = await universal_query_builder.fetch_domain_data(
        domain="products",
        shop_id="10",
        date_range=None
    )

    if products_data.get("success"):
        data = products_data["data"]

        print("\n1. DATABASE STATISTICS (What LLM Sees)")
        print("-" * 40)
        stats = data.get("statistics", {})
        print(json.dumps(stats, indent=2))

        print("\n2. ACTUAL PRODUCT STATUS COUNTS")
        print("-" * 40)

        # Count products by status
        status_counts = {}
        for product in data.get("products", []):
            status = product.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"Product counts by status:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")

        print("\n3. THE CONFUSION")
        print("-" * 40)
        print("When user asks: 'How many active products do I have?'")
        print("")
        print("LLM sees in statistics:")
        print(f"  - products_in_stock: {stats.get('products_in_stock', 0)} ← LLM thinks this means 'active'")
        print(f"  - total_products: {stats.get('total_products', 0)}")
        print("")
        print("But actually:")
        print(f"  - products_in_stock = products with inventory > 0 (not about status)")
        print(f"  - active products = products with status='active' = {status_counts.get('active', 0)}")

        print("\n4. WHY THIS HAPPENS")
        print("-" * 40)
        print("• 'products_in_stock' is about INVENTORY availability")
        print("• 'active products' is about PRODUCT STATUS")
        print("• These are completely different concepts:")
        print("  - A product can be active but out of stock")
        print("  - A product can be inactive but still have stock")
        print("")
        print("• The LLM incorrectly assumes 'active' means 'in stock'")
        print("• So it returns products_in_stock (0) instead of counting status='active' (102)")

        print("\n5. THE FIX")
        print("-" * 40)
        print("We now:")
        print("1. Calculate product_status_distribution = {'active': 102, 'inactive': 1, 'draft': 4}")
        print("2. Include this in the data sent to LLM")
        print("3. If LLM still says 0, we override with the correct count from product_status_distribution")
        print("4. This ensures the user gets the correct answer: 102 active products")

    await mongodb_client.disconnect()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("Issue: LLM confuses 'active products' (status) with 'products_in_stock' (inventory)")
    print("Root Cause: Ambiguous terminology - 'active' can mean different things")
    print("Solution: Explicit product_status_distribution + fallback override when LLM fails")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(show_root_cause())