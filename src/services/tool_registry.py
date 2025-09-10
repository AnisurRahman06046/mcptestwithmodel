"""
MongoDB-based tool registry for e-commerce data access.
Clean implementation using MongoDB collections and aggregation pipelines.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from src.database.mongodb import mongodb_client
import logging

logger = logging.getLogger(__name__)


class MongoDBToolRegistry:
    """Registry for e-commerce data access tools using MongoDB"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {
            "get_sales_data": self.get_sales_data,
            "get_inventory_status": self.get_inventory_status,
            "get_customer_info": self.get_customer_info,
            "get_order_details": self.get_order_details,
            "get_product_analytics": self.get_product_analytics,
            "get_revenue_report": self.get_revenue_report
        }
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        try:
            if not mongodb_client.is_connected:
                await mongodb_client.connect()
            
            db = mongodb_client.database
            result = await self.tools[tool_name](db, **parameters)
            
            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "parameters": parameters
            }
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}", exc_info=True)
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "parameters": parameters
            }
    
    async def get_sales_data(
        self, 
        db, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get sales data with optional filtering"""
        
        # Build match pipeline
        match_conditions = {}
        
        # Date filtering
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date)
            match_conditions["order_date"] = date_filter
        
        # Only include completed orders
        match_conditions["status"] = {"$in": ["completed", "fulfilled", "shipped"]}
        
        # Aggregation pipeline for sales data
        pipeline = [
            {"$match": match_conditions},
            {
                "$group": {
                    "_id": None,
                    "total_orders": {"$sum": 1},
                    "total_revenue": {"$sum": "$total_amount"},
                    "total_items": {"$sum": {"$size": "$items"}},
                    "average_order_value": {"$avg": "$total_amount"}
                }
            }
        ]
        
        # Execute aggregation
        result = await db.orders.aggregate(pipeline).to_list(length=1)
        
        if not result:
            return {
                "total_orders": 0,
                "total_revenue": 0.0,
                "total_quantity": 0,
                "average_order_value": 0.0,
                "breakdown": []
            }
        
        data = result[0]
        
        # Get breakdown by product/category if specified
        breakdown = []
        if product or category:
            breakdown = await self._get_sales_breakdown(db, match_conditions, product, category)
        
        return {
            "total_orders": data.get("total_orders", 0),
            "total_revenue": round(data.get("total_revenue", 0.0), 2),
            "total_quantity": data.get("total_items", 0),
            "average_order_value": round(data.get("average_order_value", 0.0), 2),
            "breakdown": breakdown
        }
    
    async def _get_sales_breakdown(self, db, match_conditions: dict, product: str = None, category: str = None):
        """Get sales breakdown by product or category"""
        pipeline = [
            {"$match": match_conditions},
            {"$unwind": "$items"},
        ]
        
        if product:
            pipeline.append({"$match": {"items.product_name": {"$regex": product, "$options": "i"}}})
        
        if category:
            # We'll need to join with products collection to get category
            pipeline.extend([
                {
                    "$lookup": {
                        "from": "products",
                        "localField": "items.product_id", 
                        "foreignField": "_id",
                        "as": "product_info"
                    }
                },
                {"$match": {"product_info.category": {"$regex": category, "$options": "i"}}}
            ])
        
        pipeline.extend([
            {
                "$group": {
                    "_id": "$items.product_name",
                    "quantity": {"$sum": "$items.quantity"},
                    "revenue": {"$sum": "$items.total_price"}
                }
            },
            {"$sort": {"revenue": -1}},
            {"$limit": 10}
        ])
        
        # Execute aggregation and get results
        breakdown_result = await db.orders.aggregate(pipeline).to_list(length=10)
        
        breakdown = []
        for doc in breakdown_result:
            breakdown.append({
                "product": doc["_id"],
                "quantity": doc["quantity"],
                "revenue": round(doc["revenue"], 2)
            })
        
        return breakdown
    
    async def get_inventory_status(
        self,
        db,
        product: Optional[str] = None,
        category: Optional[str] = None,
        low_stock_threshold: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get inventory status with optional filtering"""
        
        # Build match conditions
        match_conditions = {}
        
        if product:
            match_conditions["product_name"] = {"$regex": product, "$options": "i"}
        
        if low_stock_threshold is None:
            low_stock_threshold = 10
        
        # Get low stock items
        low_stock_pipeline = [
            {"$match": {**match_conditions, "available_quantity": {"$lte": low_stock_threshold}}},
            {"$sort": {"available_quantity": 1}},
            {"$limit": 20}
        ]
        
        # Execute low stock aggregation
        low_stock_result = await db.inventory.aggregate(low_stock_pipeline).to_list(length=20)
        
        low_stock_items = []
        for doc in low_stock_result:
            low_stock_items.append({
                "product_name": doc["product_name"],
                "sku": doc["product_sku"],
                "current_stock": doc["available_quantity"],
                "reorder_level": doc["reorder_level"]
            })
        
        # Get summary statistics
        summary_pipeline = [
            {"$match": match_conditions},
            {
                "$group": {
                    "_id": None,
                    "total_products": {"$sum": 1},
                    "low_stock_count": {
                        "$sum": {"$cond": [{"$lte": ["$available_quantity", low_stock_threshold]}, 1, 0]}
                    },
                    "out_of_stock_count": {
                        "$sum": {"$cond": [{"$eq": ["$available_quantity", 0]}, 1, 0]}
                    },
                    "total_inventory_value": {"$sum": {"$multiply": ["$available_quantity", "$cost_per_unit"]}}
                }
            }
        ]
        
        summary_result = await db.inventory.aggregate(summary_pipeline).to_list(length=1)
        summary = summary_result[0] if summary_result else {}
        
        return {
            "total_products": summary.get("total_products", 0),
            "low_stock_count": summary.get("low_stock_count", 0),
            "out_of_stock_count": summary.get("out_of_stock_count", 0),
            "total_inventory_value": round(summary.get("total_inventory_value", 0.0), 2),
            "low_stock_items": low_stock_items
        }
    
    async def get_customer_info(
        self,
        db,
        customer_id: Optional[str] = None,
        include_orders: bool = True,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get customer information with optional order details"""
        
        if customer_id:
            # Get specific customer
            customer = await db.customers.find_one({"customer_id": customer_id})
            if not customer:
                return {"error": "Customer not found"}
            
            customers_list = [customer]
        else:
            # Get top customers by total spent
            pipeline = [
                {"$sort": {"total_spent": -1}},
                {"$limit": limit}
            ]
            
            customers_list = await db.customers.aggregate(pipeline).to_list(length=limit)
        
        # Format customer data
        customers = []
        for customer in customers_list:
            customer_data = {
                "customer_id": customer["customer_id"],
                "name": customer["name"],
                "email": customer["email"],
                "total_orders": customer["total_orders"],
                "total_spent": customer["total_spent"],
                "loyalty_tier": customer["loyalty_tier"],
                "last_purchase_date": customer.get("last_purchase_date")
            }
            
            if include_orders and customer_id:
                # Get recent orders for specific customer
                recent_orders = []
                cursor = db.orders.find(
                    {"customer_id": customer["customer_id"]},
                    sort=[("order_date", -1)],
                    limit=5
                )
                async for order in cursor:
                    recent_orders.append({
                        "order_id": order["order_id"],
                        "order_date": order["order_date"],
                        "total_amount": order["total_amount"],
                        "status": order["status"]
                    })
                customer_data["recent_orders"] = recent_orders
            
            customers.append(customer_data)
        
        return {
            "customers": customers,
            "total_customers": len(customers)
        }
    
    async def get_order_details(
        self,
        db,
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get order details with filtering"""
        
        # Build match conditions
        match_conditions = {}
        
        if order_id:
            match_conditions["order_id"] = order_id
        
        if customer_id:
            match_conditions["customer_id"] = customer_id
        
        if status:
            match_conditions["status"] = status
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date)
            match_conditions["order_date"] = date_filter
        
        # Get orders
        cursor = db.orders.find(
            match_conditions,
            sort=[("order_date", -1)],
            limit=limit
        )
        
        orders = []
        total_value = 0
        
        async for order in cursor:
            order_data = {
                "order_id": order["order_id"],
                "customer_name": order["customer_name"],
                "customer_email": order["customer_email"],
                "order_date": order["order_date"],
                "status": order["status"],
                "total_amount": order["total_amount"],
                "items_count": len(order.get("items", [])),
                "payment_method": order.get("payment_method"),
                "shipping_cost": order.get("shipping_cost", 0)
            }
            orders.append(order_data)
            total_value += order["total_amount"]
        
        return {
            "orders": orders,
            "summary": {
                "total_orders": len(orders),
                "total_value": round(total_value, 2),
                "average_order_value": round(total_value / len(orders) if orders else 0, 2)
            }
        }
    
    async def get_product_analytics(
        self,
        db,
        product: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get product performance analytics"""
        
        # Build match conditions for orders
        match_conditions = {}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date)
            match_conditions["order_date"] = date_filter
        
        match_conditions["status"] = {"$in": ["completed", "fulfilled", "shipped"]}
        
        # Aggregation pipeline for product analytics
        pipeline = [
            {"$match": match_conditions},
            {"$unwind": "$items"}
        ]
        
        if product:
            pipeline.append({"$match": {"items.product_name": {"$regex": product, "$options": "i"}}})
        
        pipeline.extend([
            {
                "$group": {
                    "_id": {
                        "product_id": "$items.product_id",
                        "product_name": "$items.product_name",
                        "product_sku": "$items.product_sku"
                    },
                    "total_sold": {"$sum": "$items.quantity"},
                    "total_revenue": {"$sum": "$items.total_price"},
                    "avg_price": {"$avg": "$items.unit_price"},
                    "order_count": {"$sum": 1}
                }
            },
            {"$sort": {"total_revenue": -1}},
            {"$limit": 20}
        ])
        
        # Execute aggregation and get results
        aggregation_result = await db.orders.aggregate(pipeline).to_list(length=20)
        
        products = []
        for doc in aggregation_result:
            products.append({
                "product_name": doc["_id"]["product_name"],
                "sku": doc["_id"]["product_sku"],
                "total_sold": doc["total_sold"],
                "total_revenue": round(doc["total_revenue"], 2),
                "average_price": round(doc["avg_price"], 2),
                "order_count": doc["order_count"]
            })
        
        return {
            "products": products,
            "total_products_analyzed": len(products)
        }
    
    async def get_revenue_report(
        self,
        db,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """Get revenue report grouped by time period"""
        
        # Build match conditions
        match_conditions = {"status": {"$in": ["completed", "fulfilled", "shipped"]}}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date)
            match_conditions["order_date"] = date_filter
        
        # Group by time period
        group_by_format = {
            "day": {
                "year": {"$year": "$order_date"},
                "month": {"$month": "$order_date"},
                "day": {"$dayOfMonth": "$order_date"}
            },
            "week": {
                "year": {"$year": "$order_date"},
                "week": {"$week": "$order_date"}
            },
            "month": {
                "year": {"$year": "$order_date"},
                "month": {"$month": "$order_date"}
            }
        }
        
        pipeline = [
            {"$match": match_conditions},
            {
                "$group": {
                    "_id": group_by_format.get(group_by, group_by_format["day"]),
                    "revenue": {"$sum": "$total_amount"},
                    "orders": {"$sum": 1},
                    "avg_order_value": {"$avg": "$total_amount"}
                }
            },
            {"$sort": {"_id": 1}},
            {"$limit": 50}
        ]
        
        # Execute revenue aggregation
        revenue_result = await db.orders.aggregate(pipeline).to_list(length=50)
        
        revenue_data = []
        total_revenue = 0
        
        for doc in revenue_result:
            period_data = {
                "period": doc["_id"],
                "revenue": round(doc["revenue"], 2),
                "orders": doc["orders"],
                "avg_order_value": round(doc["avg_order_value"], 2)
            }
            revenue_data.append(period_data)
            total_revenue += doc["revenue"]
        
        return {
            "revenue_data": revenue_data,
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_periods": len(revenue_data),
                "avg_revenue_per_period": round(total_revenue / len(revenue_data) if revenue_data else 0, 2)
            }
        }


# Global tool registry instance
mongodb_tool_registry = MongoDBToolRegistry()