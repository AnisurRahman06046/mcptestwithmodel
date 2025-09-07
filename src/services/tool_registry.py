from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from src.models.database import Product, Customer, Order, OrderItem, Inventory
from src.database.connection import get_db_context
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for e-commerce data access tools"""
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {
            "get_sales_data": self.get_sales_data,
            "get_inventory_status": self.get_inventory_status,
            "get_customer_info": self.get_customer_info,
            "get_order_details": self.get_order_details,
            "get_product_analytics": self.get_product_analytics,
            "get_revenue_report": self.get_revenue_report
        }
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        try:
            with get_db_context() as db:
                result = self.tools[tool_name](db, **parameters)
                return {
                    "success": True,
                    "tool": tool_name,
                    "result": result,
                    "parameters": parameters
                }
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "parameters": parameters
            }
    
    def get_sales_data(
        self, 
        db: Session,
        product: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """Retrieve sales data with flexible filtering"""
        
        query = db.query(
            OrderItem.quantity,
            OrderItem.unit_price,
            OrderItem.discount,
            Order.order_date,
            Product.name.label('product_name'),
            Product.category
        ).join(Order).join(Product).filter(Order.status == "fulfilled")
        
        # Apply filters
        if product:
            query = query.filter(Product.name.ilike(f"%{product}%"))
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Order.order_date >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Order.order_date <= end_dt)
        
        results = query.all()
        
        if not results:
            return {
                "total_quantity": 0,
                "total_revenue": 0.0,
                "average_order_value": 0.0,
                "breakdown": [],
                "message": "No sales data found for the specified criteria"
            }
        
        # Calculate totals
        total_quantity = sum(r.quantity for r in results)
        total_revenue = sum((r.quantity * r.unit_price) - r.discount for r in results)
        
        # Group by period
        breakdown = self._group_sales_by_period(results, group_by)
        
        return {
            "total_quantity": total_quantity,
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(total_revenue / len(results), 2) if results else 0,
            "period_count": len(breakdown),
            "breakdown": breakdown
        }
    
    def get_inventory_status(
        self,
        db: Session,
        product: Optional[str] = None,
        category: Optional[str] = None,
        low_stock_threshold: int = 10
    ) -> Dict[str, Any]:
        """Check inventory status with low stock alerts"""
        
        query = db.query(Inventory, Product).join(Product)
        
        if product:
            query = query.filter(Product.name.ilike(f"%{product}%"))
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))
        
        results = query.all()
        
        inventory_data = []
        low_stock_items = []
        out_of_stock_items = []
        total_value = 0
        
        for inv, prod in results:
            item_value = inv.quantity * (inv.cost_per_unit or prod.price * 0.6)
            total_value += item_value
            
            item_data = {
                "product": prod.name,
                "category": prod.category,
                "current_stock": inv.quantity,
                "reserved": inv.reserved_quantity,
                "available": inv.quantity - inv.reserved_quantity,
                "reorder_level": inv.reorder_level,
                "max_stock": inv.max_stock_level,
                "value": round(item_value, 2),
                "supplier": inv.supplier
            }
            
            if inv.quantity == 0:
                item_data["status"] = "out_of_stock"
                out_of_stock_items.append(item_data)
            elif inv.quantity <= low_stock_threshold:
                item_data["status"] = "low_stock"
                low_stock_items.append(item_data)
            else:
                item_data["status"] = "in_stock"
            
            inventory_data.append(item_data)
        
        return {
            "total_products": len(inventory_data),
            "total_value": round(total_value, 2),
            "low_stock_count": len(low_stock_items),
            "out_of_stock_count": len(out_of_stock_items),
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items,
            "all_inventory": inventory_data[:20]  # Limit for response size
        }
    
    def get_customer_info(
        self,
        db: Session,
        customer_id: Optional[str] = None,
        email: Optional[str] = None,
        include_orders: bool = True
    ) -> Dict[str, Any]:
        """Retrieve customer information and analytics"""
        
        query = db.query(Customer)
        
        if customer_id:
            query = query.filter(Customer.id == int(customer_id))
        elif email:
            query = query.filter(Customer.email.ilike(f"%{email}%"))
        else:
            # Return top customers by total spent
            query = query.order_by(desc(Customer.total_spent)).limit(10)
        
        customers = query.all()
        
        if not customers:
            return {"message": "No customers found matching criteria"}
        
        customer_data = []
        for customer in customers:
            data = {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
                "city": customer.city,
                "country": customer.country,
                "total_orders": customer.total_orders,
                "total_spent": customer.total_spent,
                "loyalty_tier": customer.loyalty_tier,
                "member_since": customer.created_at.isoformat() if customer.created_at else None,
                "last_purchase": customer.last_purchase_date.isoformat() if customer.last_purchase_date else None
            }
            
            if include_orders:
                recent_orders = db.query(Order).filter(
                    Order.customer_id == customer.id
                ).order_by(desc(Order.order_date)).limit(5).all()
                
                data["recent_orders"] = [
                    {
                        "id": order.id,
                        "date": order.order_date.isoformat(),
                        "total": order.total_amount,
                        "status": order.status,
                        "items_count": len(order.order_items)
                    }
                    for order in recent_orders
                ]
            
            customer_data.append(data)
        
        return {
            "customers": customer_data,
            "count": len(customer_data)
        }
    
    def get_order_details(
        self,
        db: Session,
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve order information with filtering"""
        
        query = db.query(Order).join(Customer)
        
        if order_id:
            query = query.filter(Order.id == int(order_id))
        if customer_id:
            query = query.filter(Order.customer_id == int(customer_id))
        if status:
            query = query.filter(Order.status == status)
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Order.order_date >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Order.order_date <= end_dt)
        
        orders = query.order_by(desc(Order.order_date)).limit(50).all()
        
        if not orders:
            return {"message": "No orders found matching criteria"}
        
        order_data = []
        total_value = 0
        status_summary = {}
        
        for order in orders:
            # Get order items
            items = []
            for item in order.order_items:
                items.append({
                    "product": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "discount": item.discount,
                    "subtotal": (item.quantity * item.unit_price) - item.discount
                })
            
            order_info = {
                "id": order.id,
                "customer_name": order.customer.name,
                "customer_email": order.customer.email,
                "order_date": order.order_date.isoformat(),
                "status": order.status,
                "total_amount": order.total_amount,
                "payment_method": order.payment_method,
                "shipping_cost": order.shipping_cost,
                "discount": order.discount_applied,
                "items": items,
                "items_count": len(items)
            }
            
            if order.fulfilled_date:
                order_info["fulfilled_date"] = order.fulfilled_date.isoformat()
            
            order_data.append(order_info)
            total_value += order.total_amount
            
            # Update status summary
            status_summary[order.status] = status_summary.get(order.status, 0) + 1
        
        return {
            "orders": order_data,
            "summary": {
                "total_orders": len(order_data),
                "total_value": round(total_value, 2),
                "average_order_value": round(total_value / len(order_data), 2) if order_data else 0,
                "status_breakdown": status_summary
            }
        }
    
    def get_product_analytics(
        self,
        db: Session,
        product: Optional[str] = None,
        category: Optional[str] = None,
        metric: str = "sales",
        period: str = "month"
    ) -> Dict[str, Any]:
        """Generate product performance analytics"""
        
        # Get time period
        end_date = datetime.now()
        if period == "week":
            start_date = end_date - timedelta(weeks=1)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        # Base query for product performance
        query = db.query(
            Product.name,
            Product.category,
            Product.price,
            func.sum(OrderItem.quantity).label('total_sold'),
            func.sum((OrderItem.quantity * OrderItem.unit_price) - OrderItem.discount).label('revenue'),
            func.count(OrderItem.id).label('order_count')
        ).join(OrderItem).join(Order).filter(
            and_(
                Order.status == "fulfilled",
                Order.order_date >= start_date,
                Order.order_date <= end_date
            )
        )
        
        if product:
            query = query.filter(Product.name.ilike(f"%{product}%"))
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))
        
        query = query.group_by(Product.id).order_by(desc('revenue'))
        
        results = query.all()
        
        analytics = []
        for result in results:
            analytics.append({
                "product": result.name,
                "category": result.category,
                "price": result.price,
                "units_sold": result.total_sold,
                "revenue": round(result.revenue, 2),
                "orders": result.order_count,
                "avg_quantity_per_order": round(result.total_sold / result.order_count, 2) if result.order_count else 0
            })
        
        return {
            "period": f"{period} ({start_date.date()} to {end_date.date()})",
            "products": analytics[:20],  # Top 20 products
            "total_products_analyzed": len(analytics)
        }
    
    def get_revenue_report(
        self,
        db: Session,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "category",
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive revenue analysis"""
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        else:
            end_date = datetime.fromisoformat(end_date)
        
        if not start_date:
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.fromisoformat(start_date)
        
        # Revenue by grouping
        if group_by == "category":
            group_field = Product.category
        elif group_by == "product":
            group_field = Product.name
        else:  # customer
            group_field = Customer.name
        
        query = db.query(
            group_field.label('group_name'),
            func.sum((OrderItem.quantity * OrderItem.unit_price) - OrderItem.discount).label('revenue'),
            func.sum(OrderItem.quantity).label('units'),
            func.count(func.distinct(Order.id)).label('orders')
        ).join(Order).join(Product)
        
        if group_by == "customer":
            query = query.join(Customer)
        
        query = query.filter(
            and_(
                Order.status == "fulfilled",
                Order.order_date >= start_date,
                Order.order_date <= end_date
            )
        ).group_by(group_field).order_by(desc('revenue'))
        
        results = query.all()
        
        revenue_data = []
        total_revenue = 0
        total_units = 0
        
        for result in results:
            revenue_data.append({
                group_by: result.group_name,
                "revenue": round(result.revenue, 2),
                "units_sold": result.units,
                "orders": result.orders,
                "avg_order_value": round(result.revenue / result.orders, 2) if result.orders else 0
            })
            total_revenue += result.revenue
            total_units += result.units
        
        # Add percentage of total
        for item in revenue_data:
            item["percentage_of_total"] = round((item["revenue"] / total_revenue) * 100, 1) if total_revenue else 0
        
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_units": total_units,
                "grouped_by": group_by,
                "top_performers": revenue_data[:10]
            },
            "breakdown": revenue_data
        }
        
        if include_trends and len(revenue_data) > 0:
            report["insights"] = self._generate_revenue_insights(revenue_data, group_by)
        
        return report
    
    def _group_sales_by_period(self, results, group_by: str) -> List[Dict]:
        """Group sales data by time period"""
        grouped = {}
        
        for result in results:
            if group_by == "day":
                key = result.order_date.date().isoformat()
            elif group_by == "week":
                # Get Monday of the week
                monday = result.order_date.date() - timedelta(days=result.order_date.weekday())
                key = monday.isoformat()
            elif group_by == "month":
                key = result.order_date.strftime("%Y-%m")
            else:  # year
                key = str(result.order_date.year)
            
            if key not in grouped:
                grouped[key] = {"quantity": 0, "revenue": 0.0}
            
            grouped[key]["quantity"] += result.quantity
            grouped[key]["revenue"] += (result.quantity * result.unit_price) - result.discount
        
        return [
            {
                "period": period,
                "quantity": data["quantity"],
                "revenue": round(data["revenue"], 2)
            }
            for period, data in sorted(grouped.items())
        ]
    
    def _generate_revenue_insights(self, revenue_data: List[Dict], group_by: str) -> List[str]:
        """Generate insights from revenue data"""
        insights = []
        
        if revenue_data:
            top_performer = revenue_data[0]
            insights.append(f"Top performing {group_by}: {top_performer[group_by]} with ${top_performer['revenue']} ({top_performer['percentage_of_total']}% of total)")
            
            if len(revenue_data) > 1:
                total_top_3 = sum(item['percentage_of_total'] for item in revenue_data[:3])
                insights.append(f"Top 3 {group_by}s account for {total_top_3}% of total revenue")
            
            avg_revenue = sum(item['revenue'] for item in revenue_data) / len(revenue_data)
            above_avg = len([item for item in revenue_data if item['revenue'] > avg_revenue])
            insights.append(f"{above_avg} out of {len(revenue_data)} {group_by}s performed above average")
        
        return insights


# Global tool registry instance
tool_registry = ToolRegistry()