#!/usr/bin/env python3
"""
Validate database query results against API responses
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.mongodb import mongodb_client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def validate_queries():
    """
    Validate all query results by directly querying the database
    """
    print("=" * 60)
    print("DATABASE QUERY VALIDATION")
    print("=" * 60)

    try:
        # Connect to MongoDB
        await mongodb_client.connect()
        db = mongodb_client.database

        # Shop ID (adjust if needed)
        shop_id = 10

        # 1. VALIDATE LAST MONTH'S SALES (September 2025)
        print("\n1. LAST MONTH'S SALES (September 2025)")
        print("-" * 40)

        today = datetime.now()
        first_day_of_current_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)

        print(f"   Date Range: {first_day_of_last_month.isoformat()} to {last_day_of_last_month.isoformat()}")

        # Query orders for last month
        orders_filter = {
            "shop_id": shop_id,
            "created_at": {
                "$gte": first_day_of_last_month.isoformat(),
                "$lte": last_day_of_last_month.isoformat() + "T23:59:59"
            }
        }

        orders_cursor = db.order.find(orders_filter)
        orders = await orders_cursor.to_list(length=None)

        total_sales = 0
        for order in orders:
            if order.get("status") not in ["Cancelled", "Refunded"]:
                total_sales += order.get("total_amount", 0)

        print(f"   Orders found: {len(orders)}")
        print(f"   Total Sales: ${total_sales:.2f}")
        print(f"   ✓ API Response: $0.00 {'✓ MATCHES' if total_sales == 0 else '✗ MISMATCH'}")

        # 2. VALIDATE MAY SALES
        print("\n2. MAY 2025 SALES")
        print("-" * 40)

        may_start = datetime(2025, 5, 1)
        may_end = datetime(2025, 5, 31, 23, 59, 59)

        print(f"   Date Range: {may_start.isoformat()} to {may_end.isoformat()}")

        may_filter = {
            "shop_id": shop_id,
            "created_at": {
                "$gte": may_start.isoformat(),
                "$lte": may_end.isoformat()
            }
        }

        may_cursor = db.order.find(may_filter)
        may_orders = await may_cursor.to_list(length=None)

        may_sales = 0
        for order in may_orders:
            if order.get("status") not in ["Cancelled", "Refunded"]:
                may_sales += order.get("total_amount", 0)

        print(f"   Orders found: {len(may_orders)}")
        print(f"   Total Sales: ${may_sales:.2f}")
        print(f"   ✓ API Response: $0.00 {'✓ MATCHES' if may_sales == 0 else '✗ MISMATCH'}")

        # 3. VALIDATE ACTIVE PRODUCTS
        print("\n3. ACTIVE PRODUCTS COUNT")
        print("-" * 40)

        # Count products with status = 'active'
        active_filter = {
            "shop_id": shop_id,
            "status": "active"
        }

        active_count = await db.product.count_documents(active_filter)

        print(f"   Active Products: {active_count}")
        print(f"   ✓ API Response: 0 {'✓ MATCHES' if active_count == 0 else '✗ MISMATCH'}")

        # Check if there's a different status field name
        all_products = await db.product.find({"shop_id": shop_id}).to_list(length=10)
        if all_products:
            print(f"   Sample product statuses:")
            for p in all_products[:3]:
                status = p.get("status", "NO_STATUS_FIELD")
                print(f"     - Product {p.get('_id')}: status='{status}'")

        # 4. VALIDATE TOTAL PRODUCTS
        print("\n4. TOTAL PRODUCTS COUNT")
        print("-" * 40)

        total_filter = {"shop_id": shop_id}
        total_count = await db.product.count_documents(total_filter)

        print(f"   Total Products: {total_count}")
        print(f"   ✓ API Response: 107 {'✓ MATCHES' if total_count == 107 else '✗ MISMATCH'}")

        if total_count > 0:
            # Show product distribution by status
            pipeline = [
                {"$match": {"shop_id": shop_id}},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]

            status_cursor = db.product.aggregate(pipeline)
            status_dist = await status_cursor.to_list(length=None)

            print(f"   Product distribution by status:")
            for item in status_dist:
                print(f"     - {item['_id'] or 'null'}: {item['count']} products")

        # 5. ADDITIONAL VALIDATION - Check if products exist but with null/empty query results
        print("\n5. ADDITIONAL VALIDATION")
        print("-" * 40)

        # Check for products without shop_id filter
        total_products_all = await db.product.count_documents({})
        print(f"   Total products (all shops): {total_products_all}")

        # Check different shop_ids
        pipeline = [
            {"$group": {
                "_id": "$shop_id",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]

        shop_cursor = db.product.aggregate(pipeline)
        shop_dist = await shop_cursor.to_list(length=10)

        if shop_dist:
            print(f"   Product distribution by shop_id:")
            for item in shop_dist[:5]:
                print(f"     - Shop {item['_id']}: {item['count']} products")

        # Check collections
        print("\n6. DATABASE COLLECTIONS")
        print("-" * 40)

        collections = await db.list_collection_names()
        for collection in collections:
            count = await db[collection].count_documents({})
            print(f"   {collection}: {count} documents")

        print("\n" + "=" * 60)
        print("VALIDATION COMPLETE")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
    finally:
        if mongodb_client.is_connected:
            await mongodb_client.disconnect()


if __name__ == "__main__":
    asyncio.run(validate_queries())