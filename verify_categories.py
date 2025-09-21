#!/usr/bin/env python3
"""
Verify category counts from database
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    # Import inside async function to avoid import issues
    from src.database.mongodb import mongodb_client

    try:
        db = mongodb_client.db

        print("=" * 60)
        print("CATEGORY COUNT VERIFICATION")
        print("=" * 60)

        # 1. Count from category collection
        cat_collection_count = await db.category.count_documents({'shop_id': 10})
        print(f"\n1. Category collection count: {cat_collection_count}")

        # Get sample categories from collection
        cat_samples = await db.category.find({'shop_id': 10}).limit(5).to_list(length=5)
        print("   Sample categories from collection:")
        for cat in cat_samples:
            print(f"   - {cat.get('name', 'unnamed')} (id: {cat.get('_id')})")

        # 2. Unique categories from products (including null)
        pipeline = [
            {'$match': {'shop_id': 10}},
            {'$group': {'_id': '$category'}},
            {'$sort': {'_id': 1}}
        ]
        unique_cats_raw = await db.product.aggregate(pipeline).to_list(length=None)
        print(f"\n2. Unique categories in products (including null): {len(unique_cats_raw)}")

        # 3. Unique categories excluding null/empty
        unique_cats_valid = [c['_id'] for c in unique_cats_raw if c['_id']]
        print(f"\n3. Unique categories in products (excluding null): {len(unique_cats_valid)}")
        print("   First 10 unique categories from products:")
        for i, cat in enumerate(unique_cats_valid[:10], 1):
            print(f"   {i}. {cat}")

        # 4. Check for null/empty categories
        null_count = len([c for c in unique_cats_raw if not c['_id']])
        if null_count > 0:
            print(f"\n4. Products with null/empty category: {null_count} group(s)")

        # 5. Compare both sources
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print(f"- Category collection has: {cat_collection_count} categories")
        print(f"- Products use: {len(unique_cats_valid)} unique categories")
        print(f"- Difference: {abs(cat_collection_count - len(unique_cats_valid))} categories")

        if cat_collection_count != len(unique_cats_valid):
            print("\nPOSSIBLE REASONS FOR DIFFERENCE:")
            if cat_collection_count > len(unique_cats_valid):
                print("- Some categories in collection are not used by any products")
            else:
                print("- Some products have categories not in the category collection")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())