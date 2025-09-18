"""
Universal Query Builder System
Fetches complete datasets and lets LLM process them according to the query
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from src.database.mongodb import mongodb_client
import logging

logger = logging.getLogger(__name__)


class UniversalQueryBuilder:
    """
    Universal query builder that fetches complete datasets for each domain.
    The LLM will then process this data according to the specific user query.
    """

    def __init__(self):
        self.domain_builders = {
            "products": self._build_products_query,
            "sales": self._build_sales_query,
            "inventory": self._build_inventory_query,
            "customers": self._build_customers_query,
            "orders": self._build_orders_query
        }

    async def fetch_domain_data(self, domain: str, shop_id: str, date_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Fetch complete dataset for a domain

        Args:
            domain: The data domain (products, sales, inventory, customers, orders)
            shop_id: Shop ID for filtering
            date_range: Optional date range filter

        Returns:
            Complete dataset for the domain
        """
        if domain not in self.domain_builders:
            raise ValueError(f"Unknown domain: {domain}")

        try:
            if not mongodb_client.is_connected:
                await mongodb_client.connect()

            db = mongodb_client.database

            # Build and execute domain-specific query
            query_builder = self.domain_builders[domain]
            result = await query_builder(db, shop_id, date_range)

            return {
                "success": True,
                "domain": domain,
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error fetching {domain} data: {e}", exc_info=True)
            return {
                "success": False,
                "domain": domain,
                "error": str(e)
            }

    async def _build_products_query(self, db, shop_id: str, date_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build and execute comprehensive products query
        Returns ALL product-related data
        """
        shop_filter = {"shop_id": int(shop_id)} if shop_id else {}

        # 1. Get ALL products
        products_cursor = db.product.find(shop_filter)
        all_products = await products_cursor.to_list(length=None)

        # 2. Get ALL SKUs for pricing
        sku_cursor = db.sku.find(shop_filter)
        all_skus = await sku_cursor.to_list(length=None)

        # 3. Get ALL categories
        categories_cursor = db.category.find(shop_filter)
        all_categories = await categories_cursor.to_list(length=None)

        # 4. Get ALL brands
        brands_cursor = db.brand.find(shop_filter)
        all_brands = await brands_cursor.to_list(length=None)

        # 5. Get inventory for ALL products
        inventory_cursor = db.warehouse.find(shop_filter)
        all_inventory = await inventory_cursor.to_list(length=None)

        # 6. If date range provided, get sales data for products
        product_sales = []
        if date_range and date_range.get("start") and date_range.get("end"):
            match_conditions = {
                "shop_id": int(shop_id) if shop_id else {"$exists": True},
                "created_at": {
                    "$gte": date_range["start"],
                    "$lte": date_range["end"] + "T23:59:59"
                },
                "status": {"$nin": ["Cancelled", "Refunded"]}
            }

            # Get product sales performance
            pipeline = [
                {"$match": match_conditions},
                {"$unwind": "$items"},
                {"$group": {
                    "_id": "$items.product_id",
                    "product_name": {"$first": "$items.product_name"},
                    "total_sold": {"$sum": "$items.quantity"},
                    "total_revenue": {"$sum": "$items.total_price"},
                    "order_count": {"$sum": 1},
                    "avg_selling_price": {"$avg": "$items.unit_price"}
                }}
            ]

            cursor = await db.order.aggregate(pipeline)
            product_sales = await cursor.to_list(length=None)

        # Build complete product dataset
        return {
            "products": all_products,
            "skus": all_skus,
            "categories": all_categories,
            "brands": all_brands,
            "inventory": all_inventory,
            "product_sales": product_sales,
            "statistics": {
                "total_products": len(all_products),
                "total_skus": len(all_skus),
                "total_categories": len(all_categories),
                "total_brands": len(all_brands),
                "products_in_stock": len([i for i in all_inventory if i.get("available_quantity", 0) > 0])
            }
        }

    async def _build_sales_query(self, db, shop_id: str, date_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build and execute comprehensive sales query
        Returns ALL sales-related data
        """
        # Default to last 90 days if no date range
        if not date_range or not date_range.get("start"):
            ninety_days_ago = (datetime.now() - timedelta(days=90)).isoformat()
            date_range = {
                "start": ninety_days_ago,
                "end": datetime.now().isoformat()
            }

        match_conditions = {
            "shop_id": int(shop_id) if shop_id else {"$exists": True},
            "created_at": {
                "$gte": date_range["start"],
                "$lte": date_range["end"] + "T23:59:59"
            }
        }

        # 1. Get ALL orders in date range
        orders_cursor = db.order.find(match_conditions)
        all_orders = await orders_cursor.to_list(length=None)

        # 2. Get ALL order items
        order_items = []
        for order in all_orders:
            items = order.get("items", [])
            for item in items:
                item["order_id"] = order["order_id"]
                item["order_date"] = order.get("created_at")
                item["order_status"] = order.get("status")
                order_items.append(item)

        # 3. Aggregate sales by day
        daily_sales = {}
        for order in all_orders:
            if order.get("status") not in ["Cancelled", "Refunded"]:
                date_str = order.get("created_at", "")[:10]  # Get YYYY-MM-DD
                if date_str not in daily_sales:
                    daily_sales[date_str] = {
                        "date": date_str,
                        "orders": 0,
                        "revenue": 0,
                        "items_sold": 0
                    }
                daily_sales[date_str]["orders"] += 1
                daily_sales[date_str]["revenue"] += order.get("grand_total", 0)
                daily_sales[date_str]["items_sold"] += len(order.get("items", []))

        # 4. Get customer purchase data
        customer_purchases = {}
        for order in all_orders:
            customer_id = order.get("customer_id")
            if customer_id:
                if customer_id not in customer_purchases:
                    customer_purchases[customer_id] = {
                        "customer_id": customer_id,
                        "customer_name": order.get("customer_name"),
                        "orders": 0,
                        "total_spent": 0
                    }
                customer_purchases[customer_id]["orders"] += 1
                customer_purchases[customer_id]["total_spent"] += order.get("grand_total", 0)

        return {
            "orders": all_orders,
            "order_items": order_items,
            "daily_sales": list(daily_sales.values()),
            "customer_purchases": list(customer_purchases.values()),
            "statistics": {
                "total_orders": len(all_orders),
                "total_revenue": sum(o.get("grand_total", 0) for o in all_orders if o.get("status") not in ["Cancelled", "Refunded"]),
                "cancelled_orders": len([o for o in all_orders if o.get("status") in ["Cancelled", "Refunded"]]),
                "unique_customers": len(customer_purchases),
                "date_range": date_range
            }
        }

    async def _build_inventory_query(self, db, shop_id: str, date_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build and execute comprehensive inventory query
        Returns ALL inventory-related data
        """
        shop_filter = {"shop_id": int(shop_id)} if shop_id else {}

        # 1. Get ALL warehouse/inventory records
        warehouse_cursor = db.warehouse.find(shop_filter)
        all_inventory = await warehouse_cursor.to_list(length=None)

        # 2. Get product details for inventory items
        product_ids = list(set(item.get("product_id") for item in all_inventory if item.get("product_id")))
        products_cursor = db.product.find({"id": {"$in": product_ids}})
        products = await products_cursor.to_list(length=None)
        product_map = {p["id"]: p for p in products}

        # 3. Enhance inventory with product details
        enhanced_inventory = []
        for item in all_inventory:
            enhanced_item = item.copy()
            if item.get("product_id") in product_map:
                product = product_map[item["product_id"]]
                enhanced_item["product_details"] = {
                    "name": product.get("name"),
                    "category_id": product.get("category_id"),
                    "brand_id": product.get("brand_id"),
                    "status": product.get("status")
                }
            enhanced_inventory.append(enhanced_item)

        # 4. Calculate inventory metrics
        low_stock_items = [i for i in all_inventory if i.get("available_quantity", 0) <= i.get("reorder_level", 10)]
        out_of_stock_items = [i for i in all_inventory if i.get("available_quantity", 0) == 0]
        overstocked_items = [i for i in all_inventory if i.get("available_quantity", 0) > i.get("reorder_level", 10) * 3]

        return {
            "inventory": enhanced_inventory,
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items,
            "overstocked_items": overstocked_items,
            "statistics": {
                "total_items": len(all_inventory),
                "total_units": sum(i.get("available_quantity", 0) for i in all_inventory),
                "total_value": sum(i.get("available_quantity", 0) * i.get("cost_per_unit", 0) for i in all_inventory),
                "low_stock_count": len(low_stock_items),
                "out_of_stock_count": len(out_of_stock_items),
                "overstocked_count": len(overstocked_items)
            }
        }

    async def _build_customers_query(self, db, shop_id: str, date_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build and execute comprehensive customers query
        Returns ALL customer-related data
        """
        shop_filter = {"shop_id": int(shop_id)} if shop_id else {}

        # 1. Get ALL customers
        customers_cursor = db.customer.find(shop_filter)
        all_customers = await customers_cursor.to_list(length=None)

        # 2. Get order history for date range if provided
        customer_orders = {}
        if date_range and date_range.get("start") and date_range.get("end"):
            order_filter = {
                **shop_filter,
                "created_at": {
                    "$gte": date_range["start"],
                    "$lte": date_range["end"] + "T23:59:59"
                }
            }
            orders_cursor = db.order.find(order_filter)
            orders = await orders_cursor.to_list(length=None)

            for order in orders:
                customer_id = order.get("customer_id")
                if customer_id:
                    if customer_id not in customer_orders:
                        customer_orders[customer_id] = []
                    customer_orders[customer_id].append({
                        "order_id": order.get("order_id"),
                        "date": order.get("created_at"),
                        "total": order.get("grand_total"),
                        "status": order.get("status")
                    })

        # 3. Enhance customer data with order history
        enhanced_customers = []
        for customer in all_customers:
            enhanced_customer = customer.copy()
            customer_id = customer.get("customer_id")
            if customer_id in customer_orders:
                enhanced_customer["recent_orders"] = customer_orders[customer_id]
            enhanced_customers.append(enhanced_customer)

        # 4. Customer segmentation
        vip_customers = [c for c in all_customers if c.get("total_spent", 0) > 5000]
        regular_customers = [c for c in all_customers if 1000 < c.get("total_spent", 0) <= 5000]
        new_customers = [c for c in all_customers if c.get("total_orders", 0) <= 1]

        return {
            "customers": enhanced_customers,
            "vip_customers": vip_customers,
            "regular_customers": regular_customers,
            "new_customers": new_customers,
            "statistics": {
                "total_customers": len(all_customers),
                "vip_count": len(vip_customers),
                "regular_count": len(regular_customers),
                "new_count": len(new_customers),
                "total_lifetime_value": sum(c.get("total_spent", 0) for c in all_customers)
            }
        }

    async def _build_orders_query(self, db, shop_id: str, date_range: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Build and execute comprehensive orders query
        Returns ALL order-related data
        """
        # Default to last 30 days if no date range
        if not date_range or not date_range.get("start"):
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            date_range = {
                "start": thirty_days_ago,
                "end": datetime.now().isoformat()
            }

        match_conditions = {
            "shop_id": int(shop_id) if shop_id else {"$exists": True},
            "created_at": {
                "$gte": date_range["start"],
                "$lte": date_range["end"] + "T23:59:59"
            }
        }

        # 1. Get ALL orders
        orders_cursor = db.order.find(match_conditions)
        all_orders = await orders_cursor.to_list(length=None)

        # 2. Group by status
        orders_by_status = {}
        for order in all_orders:
            status = order.get("status", "Unknown")
            if status not in orders_by_status:
                orders_by_status[status] = []
            orders_by_status[status].append(order)

        # 3. Group by payment method
        orders_by_payment = {}
        for order in all_orders:
            payment = order.get("payment_method", "Unknown")
            if payment not in orders_by_payment:
                orders_by_payment[payment] = []
            orders_by_payment[payment].append(order)

        # 4. Group by shipping method
        orders_by_shipping = {}
        for order in all_orders:
            shipping = order.get("shipping_method", "Unknown")
            if shipping not in orders_by_shipping:
                orders_by_shipping[shipping] = []
            orders_by_shipping[shipping].append(order)

        return {
            "orders": all_orders,
            "orders_by_status": orders_by_status,
            "orders_by_payment": orders_by_payment,
            "orders_by_shipping": orders_by_shipping,
            "statistics": {
                "total_orders": len(all_orders),
                "total_revenue": sum(o.get("grand_total", 0) for o in all_orders),
                "average_order_value": sum(o.get("grand_total", 0) for o in all_orders) / len(all_orders) if all_orders else 0,
                "status_counts": {status: len(orders) for status, orders in orders_by_status.items()},
                "payment_counts": {payment: len(orders) for payment, orders in orders_by_payment.items()},
                "date_range": date_range
            }
        }


# Global instance
universal_query_builder = UniversalQueryBuilder()